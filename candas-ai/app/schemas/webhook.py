from pydantic import BaseModel, Field
from app.models.enums import WebhookEventType

class WebhookIngestRequest(BaseModel):
    event_type: WebhookEventType
    payload: dict = Field(default_factory=dict)
