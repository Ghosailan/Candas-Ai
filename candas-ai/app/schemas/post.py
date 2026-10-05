from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.enums import Platform, PostStatus

class PostSchema(BaseModel):
    id: UUID | None = None
    campaign_id: UUID | None = None
    platform: Platform
    copy: str
    image_prompt: str | None = None
    image_url: str | None = None
    status: PostStatus = PostStatus.draft
    compliance_flags: dict = {}
    reflection_score: float | None = None

class PublishResult(BaseModel):
    platform: Platform
    platform_post_id: str
    platform_post_url: str | None = None
    published_at: datetime

class SchedulePostRequest(BaseModel):
    publish_at: datetime

class PostUpdateRequest(BaseModel):
    copy: str | None = None
    image_prompt: str | None = None
    image_url: str | None = None
    publish_at: datetime | None = None

class PostScheduleResponse(BaseModel):
    post_id: UUID
    publish_at: datetime | None = None
    publishing_status: str | None = None

class RecommendedPostTime(BaseModel):
    post_id: UUID
    platform: str
    recommended_publish_at: datetime
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)

class PostResponse(PostSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {'from_attributes': True}
