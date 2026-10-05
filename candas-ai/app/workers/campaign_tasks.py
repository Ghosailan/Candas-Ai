import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from structlog import get_logger

from app.agents.graph import graph
from app.database import make_worker_sessionmaker, override_sessionmaker
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, PostStatus, PublishingStatus
from app.models.post import Post
from app.models.publishing_log import PublishingLog
from app.services.event_stream import publish_event
from app.services.publishing_service import (
    get_due_posts,
    publish_post_now,
    require_all_posts_scheduled,
    run_analytics_for_post,
    sync_campaign_completion,
    utcnow,
)
from app.workers.celery_app import celery_app

log = get_logger()


@celery_app.task(
    name="run_campaign_graph_task",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def run_campaign_graph_task(
    campaign_id: str,
    thread_id: str,
    initial_state: dict,
    trace_id: str | None = None,
):
    log.info(
        "task_started",
        task="run_campaign_graph_task",
        campaign_id=campaign_id,
        trace_id=trace_id,
    )

    async def _run():
        worker_engine, worker_sessionmaker = make_worker_sessionmaker()
        try:
            with override_sessionmaker(worker_sessionmaker):
                await publish_event(
                    campaign_id,
                    "graph_started",
                    detail={"thread_id": thread_id},
                    trace_id=trace_id,
                )
                await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": thread_id}},
                )
                await publish_event(
                    campaign_id,
                    "graph_completed",
                    detail={"status": "completed"},
                    trace_id=trace_id,
                )
        finally:
            await worker_engine.dispose()

    asyncio.run(_run())
    return None


async def _mark_publish_failed(
    session,
    post: Post,
    error_message: str,
) -> None:
    log_row = await session.scalar(
        select(PublishingLog).where(PublishingLog.org_id == post.org_id, PublishingLog.post_id == post.id)
    )
    if log_row is None:
        log_row = PublishingLog(
            org_id=post.org_id,
            post_id=post.id,
            platform=post.platform,
            status=PublishingStatus.failed,
        )
        session.add(log_row)
    log_row.error_message = error_message
    log_row.status = PublishingStatus.failed
    post.status = PostStatus.failed


async def _process_due_posts_for_campaign(
    campaign_id: str,
    worker_sessionmaker,
    trace_id: str | None = None,
) -> dict:
    async with worker_sessionmaker() as session:
        campaign = await session.scalar(select(Campaign).where(Campaign.id == campaign_id))
        if not campaign:
            return {"campaign_id": campaign_id, "status": "missing"}

        await publish_event(campaign_id, "node_started", node="publisher", trace_id=trace_id)
        due_rows = [
            (post, log_row)
            for post, log_row in await get_due_posts(session)
            if str(post.campaign_id) == campaign_id
        ]
        published_posts: list[Post] = []
        failures = 0
        for post, _ in due_rows:
            try:
                result = await publish_post_now(session, post, trace_id=trace_id)
                if result["status"] == "published":
                    published_posts.append(post)
            except Exception as exc:
                failures += 1
                await _mark_publish_failed(session, post, str(exc))
        await session.commit()
        await publish_event(
            campaign_id,
            "node_completed" if failures == 0 else "node_failed",
            node="publisher",
            detail={"published": len(published_posts), "failed": failures},
            trace_id=trace_id,
        )

        if published_posts:
            await publish_event(campaign_id, "node_started", node="analyst", trace_id=trace_id)
            analyzed = 0
            for post in published_posts:
                try:
                    await run_analytics_for_post(session, post, trace_id=trace_id)
                    analyzed += 1
                except Exception as exc:
                    log.warning("analytics_failed", campaign_id=campaign_id, post_id=str(post.id), error=str(exc))
            await sync_campaign_completion(session, campaign)
            await session.commit()
            await publish_event(
                campaign_id,
                "node_completed",
                node="analyst",
                detail={"analyzed": analyzed},
                trace_id=trace_id,
            )
        else:
            await sync_campaign_completion(session, campaign)
            await session.commit()

        return {
            "campaign_id": campaign_id,
            "published": len(published_posts),
            "failed": failures,
        }


@celery_app.task(
    name="run_post_approval_task",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def run_post_approval_task(campaign_id: str, trace_id: str | None = None):
    log.info(
        "task_started",
        task="run_post_approval_task",
        campaign_id=campaign_id,
        trace_id=trace_id,
    )

    async def _run():
        worker_engine, worker_sessionmaker = make_worker_sessionmaker()
        try:
            async with worker_sessionmaker() as session:
                campaign = await session.scalar(select(Campaign).where(Campaign.id == campaign_id))
                if not campaign:
                    return
                await publish_event(campaign_id, "node_started", node="scheduler", trace_id=trace_id)
                try:
                    _, posts, _ = await require_all_posts_scheduled(session, str(campaign.org_id), campaign_id)
                except Exception as exc:
                    await publish_event(
                        campaign_id,
                        "node_failed",
                        node="scheduler",
                        detail={"error": str(exc)},
                        trace_id=trace_id,
                    )
                    raise
                for post in posts:
                    if post.status != PostStatus.published:
                        post.status = PostStatus.scheduled
                campaign.status = CampaignStatus.active
                await session.commit()
                await publish_event(
                    campaign_id,
                    "node_completed",
                    node="scheduler",
                    detail={"scheduled": len(posts)},
                    trace_id=trace_id,
                )
            await _process_due_posts_for_campaign(
                campaign_id,
                worker_sessionmaker,
                trace_id=trace_id,
            )
        finally:
            await worker_engine.dispose()

    asyncio.run(_run())
    return None


@celery_app.task(
    name="publish_post_task",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def publish_post_task(post_id: str, publish_at: str, trace_id: str | None = None):
    log.info(
        "task_started",
        task="publish_post_task",
        post_id=post_id,
        publish_at=publish_at,
        trace_id=trace_id,
    )

    async def _run():
        worker_engine, worker_sessionmaker = make_worker_sessionmaker()
        try:
            campaign_id: str | None = None
            async with worker_sessionmaker() as session:
                post = await session.scalar(select(Post).where(Post.id == post_id))
                if not post:
                    return
                campaign_id = str(post.campaign_id)
                log_row = await session.scalar(
                    select(PublishingLog).where(PublishingLog.org_id == post.org_id, PublishingLog.post_id == post.id)
                )
                if publish_at == "now":
                    if log_row is None:
                        log_row = PublishingLog(
                            org_id=post.org_id,
                            post_id=post.id,
                            platform=post.platform,
                            status=PublishingStatus.scheduled,
                            scheduled_at=utcnow(),
                        )
                        session.add(log_row)
                    elif log_row.scheduled_at is None:
                        log_row.scheduled_at = utcnow()
                        log_row.status = PublishingStatus.scheduled
                else:
                    scheduled = datetime.fromisoformat(publish_at)
                    scheduled = scheduled if scheduled.tzinfo else scheduled.replace(tzinfo=timezone.utc)
                    if log_row is None:
                        log_row = PublishingLog(
                            org_id=post.org_id,
                            post_id=post.id,
                            platform=post.platform,
                            status=PublishingStatus.scheduled,
                            scheduled_at=scheduled.astimezone(timezone.utc),
                        )
                        session.add(log_row)
                    else:
                        log_row.scheduled_at = scheduled.astimezone(timezone.utc)
                        log_row.status = PublishingStatus.scheduled
                await session.commit()
            if campaign_id:
                await _process_due_posts_for_campaign(
                    campaign_id,
                    worker_sessionmaker,
                    trace_id=trace_id,
                )
        finally:
            await worker_engine.dispose()

    asyncio.run(_run())
    return None


@celery_app.task(
    name="publish_due_posts_task",
    ignore_result=True,
)
def publish_due_posts_task(trace_id: str | None = None):
    log.info("task_started", task="publish_due_posts_task", trace_id=trace_id)

    async def _run():
        worker_engine, worker_sessionmaker = make_worker_sessionmaker()
        try:
            async with worker_sessionmaker() as session:
                due_rows = await get_due_posts(session)
            campaign_ids = sorted({str(post.campaign_id) for post, _ in due_rows})
            for campaign_id in campaign_ids:
                await _process_due_posts_for_campaign(
                    campaign_id,
                    worker_sessionmaker,
                    trace_id=trace_id,
                )
        finally:
            await worker_engine.dispose()

    asyncio.run(_run())
    return None


@celery_app.task(
    name="ingest_webhook_task",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def ingest_webhook_task(event_type: str, payload: dict, trace_id: str | None = None):
    log.info(
        "task_started",
        task="ingest_webhook_task",
        event_type=event_type,
        trace_id=trace_id,
    )
    return None
