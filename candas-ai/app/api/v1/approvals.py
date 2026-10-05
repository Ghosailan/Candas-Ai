from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentUser, get_current_user, require_role
from app.database import get_session
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.enums import Role
from app.models.post import Post
from app.models.enums import ApprovalDecision, CampaignStatus, PostStatus
from app.schemas.approval import ApprovalDecisionRequest, ApprovalResponse
from app.schemas.common import success
from app.services.event_stream import publish_event
from app.services.publishing_service import require_all_posts_scheduled
from app.workers.campaign_tasks import run_post_approval_task

router = APIRouter(prefix='/approvals', tags=['approvals'])

@router.post('/{approval_id}/decision', response_model=dict)
async def approval_decision(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role(Role.approver))],
):
    campaign = await session.scalar(
        select(Campaign).where(
            Campaign.id == approval_id,
            Campaign.org_id == user.org_id,
        )
    )

    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')

    if payload.decision == ApprovalDecision.approved:
        _, posts, _ = await require_all_posts_scheduled(session, user.org_id, str(campaign.id))
    else:
        posts = (
            await session.scalars(
                select(Post).where(Post.org_id == user.org_id, Post.campaign_id == campaign.id)
            )
        ).all()

    await session.execute(
        insert(Approval)
        .values(
            id=campaign.id,
            org_id=user.org_id,
            campaign_id=campaign.id,
            reviewer_id=user.id,
            decision=payload.decision,
            feedback=payload.feedback,
        )
        .on_conflict_do_update(
            index_elements=[Approval.id],
            set_={
                'reviewer_id': user.id,
                'decision': payload.decision,
                'feedback': payload.feedback,
            },
        )
    )

    campaign.status = (
        CampaignStatus.active
        if payload.decision == ApprovalDecision.approved
        else CampaignStatus.paused
    )
    for post in posts:
        if payload.decision == ApprovalDecision.rejected and post.status != PostStatus.published:
            post.status = PostStatus.rejected
        elif payload.decision == ApprovalDecision.approved and post.status != PostStatus.published:
            post.status = PostStatus.approved

    await session.commit()
    approval = await session.scalar(select(Approval).where(Approval.id == campaign.id))
    await publish_event(
        approval_id,
        'node_completed',
        node='approval',
        detail={'decision': payload.decision.value, 'status': campaign.status.value},
        trace_id=request.state.trace_id,
    )
    if payload.decision == ApprovalDecision.approved:
        run_post_approval_task.delay(str(campaign.id), request.state.trace_id)

    return success(
        {
            'approval_id': str(approval.id),
            'campaign_id': str(campaign.id),
            'decision': payload.decision.value,
            'status': campaign.status.value,
        },
        request.state.trace_id,
    )

@router.get('/pending', response_model=dict)
async def pending_approvals(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role(Role.approver))],
):
    campaigns = (
        await session.execute(
            select(Campaign)
            .where(Campaign.org_id == user.org_id)
            .order_by(Campaign.created_at.desc())
        )
    ).scalars().all()
    pending = []
    for campaign in campaigns:
        decision = await session.scalar(
            select(Approval).where(Approval.org_id == user.org_id, Approval.campaign_id == campaign.id)
        )
        posts = (await session.scalars(select(Post).where(Post.org_id == user.org_id, Post.campaign_id == campaign.id))).all()
        if posts and not decision:
            pending.append(
                {
                    'approval_id': str(campaign.id),
                    'campaign_id': str(campaign.id),
                    'campaign_title': campaign.title,
                    'status': campaign.status.value,
                    'post_count': len(posts),
                    'platforms': campaign.platforms,
                    'created_at': campaign.created_at.isoformat(),
                }
            )
    return success(pending, request.state.trace_id)


@router.get('/campaign/{campaign_id}', response_model=dict)
async def get_campaign_approval(
    campaign_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    approval = await session.scalar(
        select(Approval).where(Approval.org_id == user.org_id, Approval.campaign_id == campaign_id)
    )
    if not approval:
        return success(None, request.state.trace_id)
    data = ApprovalResponse(
        approval_id=approval.id,
        campaign_id=approval.campaign_id,
        post_id=approval.post_id,
        decision=approval.decision,
        feedback=approval.feedback,
    )
    return success(data.model_dump(mode='json'), request.state.trace_id)
