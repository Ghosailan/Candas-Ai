from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.enums import CampaignStatus, Platform

class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    brief: str = Field(min_length=10)
    platforms: list[Platform] = Field(min_length=1)
    goals: list[str] = Field(default_factory=list)
    target_audience: dict = Field(default_factory=dict)

class CampaignResponse(BaseModel):
    id: UUID
    title: str
    brief: str
    platforms: list[str]
    goals: list[str]
    target_audience: dict
    status: CampaignStatus
    thread_id: str
    created_at: datetime

    model_config = {'from_attributes': True}

class CampaignUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    brief: str | None = Field(default=None, min_length=10)
    platforms: list[Platform] | None = None
    goals: list[str] | None = None
    target_audience: dict | None = None

class ScheduleSuggestionRequest(BaseModel):
    timezone: str = 'Asia/Riyadh'
    start_date: datetime | None = None
    end_date: datetime | None = None
    preferred_days: list[str] | None = None
    preferred_time_window: str | None = None

class CampaignRunResponse(BaseModel):
    campaign_id: UUID
    thread_id: str
    status: str
    stream_url: str
