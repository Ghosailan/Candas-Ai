from typing import Annotated, TypedDict, Optional
from langgraph.graph.message import add_messages

class CampaignState(TypedDict):
    campaign_id: str
    org_id: str
    brief: str
    goals: list[str]
    target_audience: dict
    platforms: list[str]
    brand_guidelines: str
    research_context: str
    post_drafts: list[dict]
    reflection_feedback: str
    approval_status: str
    reviewer_feedback: str
    schedule: list[dict]
    published_post_ids: list[str]
    analytics_summary: dict
    memory_context: str
    messages: Annotated[list, add_messages]
    error: Optional[str]
    reflection_score: float
    reflection_retries: int
    trace_id: str
