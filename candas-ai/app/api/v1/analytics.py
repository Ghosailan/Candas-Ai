from typing import Annotated
from sqlalchemy import func, select
from fastapi import APIRouter, Depends, Request
from app.api.deps import CurrentUser, get_current_user, require_role
from app.database import get_session
from app.models import Analytics, Post
from app.models.enums import Role
from app.schemas.common import success
from app.workers.analytics_tasks import fetch_analytics_task
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix='/analytics', tags=['analytics'])

@router.get('/{campaign_id}', response_model=dict)
async def get_analytics(
    campaign_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    rows = (
        await session.execute(
            select(Analytics, Post)
            .join(Post, Post.id == Analytics.post_id)
            .where(Post.org_id == user.org_id, Post.campaign_id == campaign_id)
        )
    ).all()
    if not rows:
        return success(
            {
                'campaign_id': campaign_id,
                'totals': {'impressions': 0, 'clicks': 0, 'reach': 0, 'engagement_rate': 0, 'conversions': 0},
                'by_platform': [],
                'best_posts': [],
                'empty': True,
                'message': 'Analytics collection runs after publish. In mock mode, this remains empty until analytics are fetched.',
            },
            request.state.trace_id,
        )

    totals = {'impressions': 0, 'clicks': 0, 'reach': 0, 'engagement_rate': 0.0, 'conversions': 0}
    by_platform: dict[str, dict] = {}
    best_posts = []
    for metric, post in rows:
        totals['impressions'] += metric.impressions
        totals['clicks'] += metric.clicks
        totals['reach'] += metric.reach
        totals['conversions'] += metric.conversions
        totals['engagement_rate'] += metric.engagement_rate
        bucket = by_platform.setdefault(
            metric.platform.value,
            {'platform': metric.platform.value, 'impressions': 0, 'clicks': 0, 'reach': 0, 'engagement_rate': 0.0, 'conversions': 0, 'posts': 0},
        )
        bucket['impressions'] += metric.impressions
        bucket['clicks'] += metric.clicks
        bucket['reach'] += metric.reach
        bucket['conversions'] += metric.conversions
        bucket['engagement_rate'] += metric.engagement_rate
        bucket['posts'] += 1
        best_posts.append(
            {
                'post_id': str(post.id),
                'platform': post.platform.value,
                'copy': post.copy[:160],
                'engagement_rate': metric.engagement_rate,
                'clicks': metric.clicks,
                'impressions': metric.impressions,
            }
        )
    count = len(rows)
    totals['engagement_rate'] = round(totals['engagement_rate'] / count, 4) if count else 0.0
    platform_rows = []
    for bucket in by_platform.values():
        bucket['engagement_rate'] = round(bucket['engagement_rate'] / max(bucket['posts'], 1), 4)
        platform_rows.append(bucket)
    best_posts.sort(key=lambda item: (item['engagement_rate'], item['clicks'], item['impressions']), reverse=True)
    return success(
        {
            'campaign_id': campaign_id,
            'totals': totals,
            'by_platform': platform_rows,
            'best_posts': best_posts[:5],
            'empty': False,
        },
        request.state.trace_id,
    )

@router.post('/{campaign_id}/refresh', response_model=dict, status_code=202)
async def refresh_analytics(campaign_id: str, request: Request, user: Annotated[CurrentUser, Depends(require_role(Role.editor))]):
    fetch_analytics_task.delay(campaign_id, request.state.trace_id)
    return success({'campaign_id': campaign_id, 'status': 'queued'}, request.state.trace_id)
