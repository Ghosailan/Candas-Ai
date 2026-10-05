import asyncio
from typing import Annotated
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentUser, get_current_user, require_role
from app.config import get_settings
from app.database import get_session
from app.models import Approval, Post, PublishingLog
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, PostStatus, PublishingStatus, Role
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignRunResponse,
    CampaignUpdate,
    ScheduleSuggestionRequest,
)
from app.schemas.common import success
from app.services.campaign_service import create_campaign, get_campaign
from app.services.event_stream import channel_for_campaign
from app.services.publishing_service import fetch_campaign_dashboard_data
from app.services.schedule_advisor import recommend_post_times

router = APIRouter(prefix='/campaigns', tags=['campaigns'])

@router.post('', response_model=dict, status_code=202)
async def create_campaign_endpoint(payload: CampaignCreate, request: Request, session: Annotated[AsyncSession, Depends(get_session)], user: Annotated[CurrentUser, Depends(require_role(Role.editor))]):
    campaign = await create_campaign(session, payload, user, request.state.trace_id)
    data = CampaignRunResponse(campaign_id=campaign.id, thread_id=campaign.thread_id, status='accepted', stream_url=f'/v1/campaigns/{campaign.id}/stream')
    return success(data.model_dump(mode='json'), request.state.trace_id)

@router.get('', response_model=dict)
async def list_campaigns(request: Request, session: Annotated[AsyncSession, Depends(get_session)], user: Annotated[CurrentUser, Depends(get_current_user)]):
    rows = (await session.scalars(select(Campaign).where(Campaign.org_id == user.org_id).order_by(Campaign.created_at.desc()))).all()
    return success([CampaignResponse.model_validate(r).model_dump(mode='json') for r in rows], request.state.trace_id)

@router.get('/{campaign_id}', response_model=dict)
async def get_campaign_endpoint(campaign_id: str, request: Request, session: Annotated[AsyncSession, Depends(get_session)], user: Annotated[CurrentUser, Depends(get_current_user)]):
    campaign = await get_campaign(session, user.org_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return success(CampaignResponse.model_validate(campaign).model_dump(mode='json'), request.state.trace_id)


@router.get('/{campaign_id}/dashboard', response_model=dict)
async def get_campaign_dashboard(
    campaign_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    dashboard = await fetch_campaign_dashboard_data(session, user.org_id, campaign_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail='Campaign not found')
    campaign = dashboard['campaign']
    approval = await session.scalar(
        select(Approval).where(Approval.org_id == user.org_id, Approval.campaign_id == campaign.id)
    )
    return success(
        {
            'campaign': CampaignResponse.model_validate(campaign).model_dump(mode='json'),
            'posts': dashboard['posts'],
            'approval': None
            if not approval
            else {
                'approval_id': str(approval.id),
                'campaign_id': str(approval.campaign_id) if approval.campaign_id else None,
                'decision': approval.decision.value,
                'feedback': approval.feedback,
                'decided_at': approval.decided_at.isoformat() if approval.decided_at else None,
            },
            'progress': dashboard['progress'],
        },
        request.state.trace_id,
    )


@router.post('/{campaign_id}/schedule-suggestions', response_model=dict)
async def schedule_suggestions(
    campaign_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    payload: ScheduleSuggestionRequest | None = None,
):
    payload = payload or ScheduleSuggestionRequest()
    campaign = await session.scalar(
        select(Campaign).where(Campaign.org_id == user.org_id, Campaign.id == campaign_id)
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    posts = (
        await session.scalars(
            select(Post).where(Post.org_id == user.org_id, Post.campaign_id == campaign_id).order_by(Post.created_at.asc())
        )
    ).all()
    suggestions = await recommend_post_times(
        campaign=campaign,
        posts=list(posts),
        timezone_name=payload.timezone,
        start_date=payload.start_date,
        end_date=payload.end_date,
        preferred_days=payload.preferred_days,
        preferred_time_window=payload.preferred_time_window,
    )
    return success(
        {
            'campaign_id': campaign_id,
            'timezone': payload.timezone,
            'suggestions': suggestions,
        },
        request.state.trace_id,
    )


@router.patch('/{campaign_id}', response_model=dict)
async def update_campaign_endpoint(
    campaign_id: str,
    payload: CampaignUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role(Role.editor))],
):
    campaign = await session.scalar(
        select(Campaign).where(Campaign.org_id == user.org_id, Campaign.id == campaign_id)
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    published_posts = await session.scalar(
        select(Post.id).where(
            Post.org_id == user.org_id,
            Post.campaign_id == campaign_id,
            Post.status == PostStatus.published,
        )
    )
    if campaign.status == CampaignStatus.completed or published_posts:
        raise HTTPException(status_code=400, detail='Completed or published campaigns cannot be edited safely.')
    updates = payload.model_dump(exclude_unset=True)
    if 'platforms' in updates and updates['platforms'] is not None:
        campaign.platforms = [platform.value for platform in updates['platforms']]
    if 'title' in updates:
        campaign.title = updates['title']
    if 'brief' in updates:
        campaign.brief = updates['brief']
    if 'goals' in updates and updates['goals'] is not None:
        campaign.goals = updates['goals']
    if 'target_audience' in updates and updates['target_audience'] is not None:
        campaign.target_audience = updates['target_audience']
    await session.commit()
    await session.refresh(campaign)
    return success(CampaignResponse.model_validate(campaign).model_dump(mode='json'), request.state.trace_id)


@router.delete('/{campaign_id}', response_model=dict)
async def delete_campaign_endpoint(
    campaign_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role(Role.editor))],
):
    campaign = await session.scalar(
        select(Campaign).where(Campaign.org_id == user.org_id, Campaign.id == campaign_id)
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    has_published = await session.scalar(
        select(PublishingLog.id).where(
            PublishingLog.org_id == user.org_id,
            PublishingLog.status == PublishingStatus.published,
            PublishingLog.post_id.in_(
                select(Post.id).where(Post.org_id == user.org_id, Post.campaign_id == campaign_id)
            ),
        )
    )
    if has_published:
        campaign.status = CampaignStatus.paused
        await session.commit()
        return success(
            {'campaign_id': campaign_id, 'status': campaign.status.value, 'deleted': False, 'cancelled': True},
            request.state.trace_id,
        )
    await session.delete(campaign)
    await session.commit()
    return success({'campaign_id': campaign_id, 'deleted': True}, request.state.trace_id)

@router.get('/{campaign_id}/stream')
async def stream_campaign(campaign_id: str, request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]):
    settings = get_settings()
    async def event_generator():
        client = redis.from_url(settings.redis_url)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel_for_campaign(campaign_id))
        last_heartbeat = 0
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    yield f'data: {message["data"].decode()}\n\n'
                now = asyncio.get_event_loop().time()
                if now - last_heartbeat >= 15:
                    yield 'data: {"event":"heartbeat"}\n\n'
                    last_heartbeat = now
        finally:
            await pubsub.unsubscribe(channel_for_campaign(campaign_id))
            await pubsub.close(); await client.aclose()
    return StreamingResponse(event_generator(), media_type='text/event-stream')
