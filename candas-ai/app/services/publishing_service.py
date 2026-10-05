from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import Analytics
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, Platform, PostStatus, PublishingStatus
from app.models.post import Post
from app.models.publishing_log import PublishingLog
from app.platforms import get_adapter
from app.schemas.analytics import AnalyticsSchema
from app.schemas.post import PostSchema


SCHEDULE_REQUIRED_MESSAGE = (
    'Please select or confirm schedule times for all posts before approving the campaign.'
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_future_publish_at(publish_at: datetime) -> datetime:
    if publish_at.tzinfo is None:
        raise HTTPException(status_code=400, detail='Schedule time must include a timezone offset.')
    if publish_at < utcnow():
        raise HTTPException(
            status_code=400,
            detail='Schedule time cannot be in the past. Choose a current or future publish time.',
        )
    return publish_at.astimezone(timezone.utc)


async def get_campaign_with_posts(
    session: AsyncSession,
    org_id: str,
    campaign_id: str,
) -> Campaign | None:
    return await session.scalar(
        select(Campaign)
        .where(Campaign.org_id == org_id, Campaign.id == campaign_id)
        .options(selectinload(Campaign.posts))
    )


async def get_schedule_log(
    session: AsyncSession,
    post_id: str | uuid.UUID,
) -> PublishingLog | None:
    return await session.scalar(
        select(PublishingLog)
        .where(PublishingLog.post_id == post_id)
        .order_by(PublishingLog.scheduled_at.desc().nullslast(), PublishingLog.published_at.desc().nullslast())
        .limit(1)
    )


async def upsert_schedule_log(
    session: AsyncSession,
    post: Post,
    publish_at: datetime,
) -> PublishingLog:
    publish_at_utc = ensure_future_publish_at(publish_at)
    log = await session.scalar(
        select(PublishingLog)
        .where(PublishingLog.org_id == post.org_id, PublishingLog.post_id == post.id)
        .order_by(PublishingLog.scheduled_at.desc().nullslast(), PublishingLog.published_at.desc().nullslast())
        .limit(1)
    )
    if log is None:
        log = PublishingLog(
            org_id=post.org_id,
            post_id=post.id,
            platform=post.platform,
            status=PublishingStatus.scheduled,
            scheduled_at=publish_at_utc,
        )
        session.add(log)
    else:
        log.platform = post.platform
        log.status = PublishingStatus.scheduled
        log.error_message = None
        log.scheduled_at = publish_at_utc
    if post.status != PostStatus.published:
        post.status = PostStatus.scheduled
    return log


async def require_all_posts_scheduled(
    session: AsyncSession,
    org_id: str,
    campaign_id: str,
) -> tuple[Campaign, list[Post], dict[uuid.UUID, PublishingLog]]:
    campaign = await get_campaign_with_posts(session, org_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    posts = list(campaign.posts)
    if not posts:
        raise HTTPException(status_code=400, detail='Campaign has no generated posts to approve.')
    logs = (
        await session.scalars(
            select(PublishingLog).where(
                PublishingLog.org_id == org_id,
                PublishingLog.post_id.in_([post.id for post in posts]),
            )
        )
    ).all()
    log_map = {log.post_id: log for log in logs}
    missing = [post for post in posts if not log_map.get(post.id) or not log_map[post.id].scheduled_at]
    if missing:
        raise HTTPException(status_code=400, detail=SCHEDULE_REQUIRED_MESSAGE)
    return campaign, posts, log_map


def serialize_post(
    post: Post,
    log: PublishingLog | None = None,
    analytics: Sequence[Analytics] | None = None,
    recommendation: dict | None = None,
) -> dict:
    analytics = analytics or []
    latest_metric = max(analytics, key=lambda item: item.fetched_at, default=None)
    return {
        'id': str(post.id),
        'campaign_id': str(post.campaign_id),
        'platform': post.platform.value,
        'copy': post.copy,
        'image_prompt': post.image_prompt,
        'image_url': post.image_url,
        'status': post.status.value,
        'compliance_flags': post.compliance_flags,
        'reflection_score': post.reflection_score,
        'created_at': post.created_at.isoformat() if post.created_at else None,
        'updated_at': post.updated_at.isoformat() if post.updated_at else None,
        'publish_at': log.scheduled_at.isoformat() if log and log.scheduled_at else None,
        'publishing_status': log.status.value if log else None,
        'published_at': log.published_at.isoformat() if log and log.published_at else None,
        'platform_post_id': log.platform_post_id if log else None,
        'platform_post_url': log.platform_post_url if log else None,
        'publishing_error': log.error_message if log else None,
        'analytics': None
        if not latest_metric
        else {
            'impressions': latest_metric.impressions,
            'clicks': latest_metric.clicks,
            'engagement_rate': latest_metric.engagement_rate,
            'reach': latest_metric.reach,
            'conversions': latest_metric.conversions,
            'fetched_at': latest_metric.fetched_at.isoformat() if latest_metric.fetched_at else None,
        },
        'recommended_schedule': recommendation,
    }


async def fetch_campaign_dashboard_data(
    session: AsyncSession,
    org_id: str,
    campaign_id: str,
) -> dict | None:
    campaign = await get_campaign_with_posts(session, org_id, campaign_id)
    if not campaign:
        return None
    post_ids = [post.id for post in campaign.posts]
    logs = []
    analytics_rows = []
    if post_ids:
        logs = (
            await session.scalars(
                select(PublishingLog).where(
                    PublishingLog.org_id == org_id,
                    PublishingLog.post_id.in_(post_ids),
                )
            )
        ).all()
        analytics_rows = (
            await session.scalars(
                select(Analytics).where(
                    Analytics.org_id == org_id,
                    Analytics.post_id.in_(post_ids),
                )
            )
        ).all()
    log_map = {log.post_id: log for log in logs}
    analytics_map: dict[uuid.UUID, list[Analytics]] = {}
    for row in analytics_rows:
        analytics_map.setdefault(row.post_id, []).append(row)
    published_count = sum(1 for post in campaign.posts if post.status == PostStatus.published)
    scheduled_count = sum(1 for post in campaign.posts if log_map.get(post.id) and log_map[post.id].scheduled_at)
    return {
        'campaign': campaign,
        'posts': [serialize_post(post, log_map.get(post.id), analytics_map.get(post.id)) for post in campaign.posts],
        'progress': {
            'completed_posts': published_count,
            'scheduled_posts': scheduled_count,
            'total_posts': len(campaign.posts),
            'percent': round((published_count / max(len(campaign.posts), 1)) * 100),
        },
    }


async def sync_campaign_completion(
    session: AsyncSession,
    campaign: Campaign,
) -> None:
    posts = (
        await session.scalars(select(Post).where(Post.campaign_id == campaign.id, Post.org_id == campaign.org_id))
    ).all()
    if not posts:
        campaign.status = CampaignStatus.active
        return
    if all(post.status == PostStatus.published for post in posts):
        published_post_ids = [post.id for post in posts]
        metrics_count = await session.scalar(
            select(func.count(Analytics.id)).where(
                Analytics.org_id == campaign.org_id,
                Analytics.post_id.in_(published_post_ids),
            )
        )
        campaign.status = (
            CampaignStatus.completed if (metrics_count or 0) >= len(published_post_ids) else CampaignStatus.active
        )
    else:
        campaign.status = CampaignStatus.active


async def run_analytics_for_post(
    session: AsyncSession,
    post: Post,
    trace_id: str | None = None,
) -> dict:
    adapter = get_adapter(post.platform, trace_id=trace_id)
    log = await get_schedule_log(session, post.id)
    since = log.published_at if log and log.published_at else utcnow()
    analytics_data: AnalyticsSchema = await adapter.get_analytics(str(post.id), since)
    await session.execute(delete(Analytics).where(Analytics.post_id == post.id))
    session.add(
        Analytics(
            org_id=post.org_id,
            post_id=post.id,
            platform=Platform(analytics_data.platform),
            impressions=analytics_data.impressions,
            clicks=analytics_data.clicks,
            engagement_rate=analytics_data.engagement_rate,
            reach=analytics_data.reach,
            conversions=analytics_data.conversions,
            fetched_at=analytics_data.fetched_at or utcnow(),
        )
    )
    return {'post_id': str(post.id), 'status': 'analytics_fetched'}


async def publish_post_now(
    session: AsyncSession,
    post: Post,
    trace_id: str | None = None,
) -> dict:
    log = await session.scalar(
        select(PublishingLog).where(PublishingLog.org_id == post.org_id, PublishingLog.post_id == post.id)
    )
    if log is None:
        log = PublishingLog(
            org_id=post.org_id,
            post_id=post.id,
            platform=post.platform,
            status=PublishingStatus.failed,
            error_message='No schedule selected for post.',
        )
        session.add(log)
        return {'post_id': str(post.id), 'status': 'missing_schedule'}
    if not log.scheduled_at:
        return {'post_id': str(post.id), 'status': 'missing_schedule'}
    if post.status == PostStatus.published:
        return {'post_id': str(post.id), 'status': 'already_published'}
    if log.scheduled_at > utcnow():
        return {'post_id': str(post.id), 'status': 'not_due', 'publish_at': log.scheduled_at.isoformat()}

    adapter = get_adapter(post.platform, trace_id=trace_id)
    result = await adapter.publish(
        PostSchema(
            id=post.id,
            campaign_id=post.campaign_id,
            platform=post.platform,
            copy=post.copy,
            image_prompt=post.image_prompt,
            image_url=post.image_url,
            status=post.status,
            compliance_flags=post.compliance_flags,
            reflection_score=post.reflection_score,
        )
    )
    log.platform = post.platform
    log.status = PublishingStatus.published
    log.platform_post_id = result.platform_post_id
    log.platform_post_url = result.platform_post_url
    log.error_message = None
    log.published_at = result.published_at.astimezone(timezone.utc)
    post.status = PostStatus.published
    return {
        'post_id': str(post.id),
        'status': 'published',
        'platform_post_id': result.platform_post_id,
        'platform_post_url': result.platform_post_url,
    }


async def get_due_posts(session: AsyncSession) -> list[tuple[Post, PublishingLog]]:
    rows = (
        await session.execute(
            select(Post, PublishingLog)
            .join(PublishingLog, PublishingLog.post_id == Post.id)
            .where(
                PublishingLog.status == PublishingStatus.scheduled,
                PublishingLog.scheduled_at.is_not(None),
                PublishingLog.scheduled_at <= utcnow(),
                Post.status != PostStatus.published,
            )
            .order_by(PublishingLog.scheduled_at.asc())
        )
    ).all()
    return [(post, log) for post, log in rows]
