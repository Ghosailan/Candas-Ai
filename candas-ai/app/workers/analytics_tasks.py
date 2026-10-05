import asyncio

from sqlalchemy import select
from structlog import get_logger

from app.database import make_worker_sessionmaker
from app.models.campaign import Campaign
from app.models.enums import PostStatus
from app.models.post import Post
from app.services.publishing_service import run_analytics_for_post, sync_campaign_completion
from app.workers.celery_app import celery_app

log = get_logger()


@celery_app.task(
    name='fetch_analytics_task',
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
)
def fetch_analytics_task(target_id: str, trace_id: str | None = None):
    log.info('task_started', task='fetch_analytics_task', target_id=target_id, trace_id=trace_id)

    async def _run():
        worker_engine, worker_sessionmaker = make_worker_sessionmaker()
        try:
            async with worker_sessionmaker() as session:
                campaign = await session.scalar(select(Campaign).where(Campaign.id == target_id))
                if campaign:
                    posts = (
                        await session.scalars(
                            select(Post).where(Post.org_id == campaign.org_id, Post.campaign_id == campaign.id)
                        )
                    ).all()
                    for post in posts:
                        if post.status == PostStatus.published:
                            await run_analytics_for_post(session, post, trace_id=trace_id)
                    await sync_campaign_completion(session, campaign)
                    await session.commit()
                    return
                post = await session.scalar(select(Post).where(Post.id == target_id))
                if not post:
                    return
                await run_analytics_for_post(session, post, trace_id=trace_id)
                related_campaign = await session.scalar(select(Campaign).where(Campaign.id == post.campaign_id))
                if related_campaign:
                    await sync_campaign_completion(session, related_campaign)
                await session.commit()
        finally:
            await worker_engine.dispose()

    asyncio.run(_run())
    return None


@celery_app.task(name='app.workers.analytics_tasks.fetch_due_analytics_task', ignore_result=True)
def fetch_due_analytics_task():
    log.info('task_started', task='fetch_due_analytics_task')
    return None
