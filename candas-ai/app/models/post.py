import uuid
from datetime import datetime
from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, Float, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import Platform, PostStatus

class Post(Base):
    __tablename__ = 'posts'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('campaigns.id', ondelete='CASCADE'), index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name='platform_enum'), nullable=False)
    copy: Mapped[str] = mapped_column(Text, nullable=False)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus, name='post_status_enum'), default=PostStatus.draft, nullable=False)
    variant: Mapped[str | None] = mapped_column(CHAR(1))
    compliance_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    reflection_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    campaign = relationship('Campaign', back_populates='posts')
