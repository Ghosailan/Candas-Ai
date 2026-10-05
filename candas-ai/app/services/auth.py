from uuid import UUID
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Campaign, Post, Approval, PublishingLog, Analytics, CampaignEmbedding, User

async def delete_user_data(session: AsyncSession, org_id: str, user_id: UUID) -> None:
    # Service-layer org filter prevents cross-tenant deletion.
    await session.execute(delete(Campaign).where(Campaign.org_id == org_id, Campaign.created_by == user_id))
    await session.execute(delete(User).where(User.org_id == org_id, User.id == user_id))
    await session.commit()
