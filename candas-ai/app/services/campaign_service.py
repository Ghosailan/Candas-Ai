import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentUser
from app.models.campaign import Campaign
from app.models.enums import CampaignStatus
from app.schemas.campaign import CampaignCreate
from app.workers.campaign_tasks import run_campaign_graph_task

async def create_campaign(session: AsyncSession, payload: CampaignCreate, user: CurrentUser, trace_id: str) -> Campaign:
    campaign_id = uuid.uuid4()
    thread_id = str(campaign_id)
    campaign = Campaign(
        id=campaign_id,
        org_id=user.org_id,
        title=payload.title,
        brief=payload.brief,
        goals=payload.goals,
        target_audience=payload.target_audience,
        platforms=[p.value for p in payload.platforms],
        status=CampaignStatus.active,
        created_by=user.id,
        thread_id=thread_id,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    initial_state = {
        'campaign_id': str(campaign.id), 'org_id': str(campaign.org_id), 'brief': campaign.brief,
        'goals': campaign.goals, 'target_audience': campaign.target_audience, 'platforms': campaign.platforms,
        'brand_guidelines': '', 'research_context': '', 'post_drafts': [], 'reflection_feedback': '',
        'approval_status': 'pending', 'reviewer_feedback': '', 'schedule': [], 'published_post_ids': [],
        'analytics_summary': {}, 'memory_context': '', 'messages': [], 'error': None, 'reflection_score': 0.0,
        'reflection_retries': 0, 'trace_id': trace_id,
    }
    run_campaign_graph_task.delay(str(campaign.id), thread_id, initial_state, trace_id)
    return campaign

async def get_campaign(session: AsyncSession, org_id: str, campaign_id: str) -> Campaign | None:
    return await session.scalar(select(Campaign).where(Campaign.org_id == org_id, Campaign.id == campaign_id))
