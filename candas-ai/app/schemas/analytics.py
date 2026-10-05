from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.enums import Platform

class AnalyticsSchema(BaseModel):
    platform: Platform
    post_id: str | UUID
    impressions: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0
    reach: int = 0
    conversions: int = 0
    fetched_at: datetime | None = None

class AnalyticsSummary(BaseModel):
    campaign_id: UUID
    totals: dict
    by_platform: dict
