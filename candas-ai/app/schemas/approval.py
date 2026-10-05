from uuid import UUID
from pydantic import BaseModel, Field
from app.models.enums import ApprovalDecision

class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    feedback: str | None = Field(default=None, max_length=5000)

class ApprovalResponse(BaseModel):
    approval_id: UUID
    campaign_id: UUID | None = None
    post_id: UUID | None = None
    decision: ApprovalDecision
    feedback: str | None = None
