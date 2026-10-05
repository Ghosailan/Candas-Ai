import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import Platform, PublishingStatus


class PublishingLog(Base):
    __tablename__ = 'publishing_logs'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('posts.id', ondelete='CASCADE'),
        index=True,
    )

    # Important:
    # Reuse the existing platform_enum used by posts.platform.
    # Do not use publishing_platform_enum because that type does not exist in PostgreSQL.
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name='platform_enum', create_type=False),
        nullable=False,
    )

    platform_post_id: Mapped[str | None] = mapped_column(Text)
    platform_post_url: Mapped[str | None] = mapped_column(Text)

    status: Mapped[PublishingStatus] = mapped_column(
        Enum(PublishingStatus, name='publishing_status_enum', create_type=False),
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))