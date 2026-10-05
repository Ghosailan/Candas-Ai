import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import CampaignStatus

class Campaign(Base):
    __tablename__ = 'campaigns'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('organisations.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    goals: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    target_audience: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    platforms: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus, name='campaign_status_enum'), default=CampaignStatus.draft, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    creator = relationship('User', back_populates='campaigns')
    posts = relationship('Post', back_populates='campaign', cascade='all, delete-orphan')
