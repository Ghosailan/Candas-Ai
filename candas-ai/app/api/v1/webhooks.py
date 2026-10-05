from fastapi import APIRouter, Header, HTTPException, Request, status
from app.config import get_settings
from app.core.security import verify_hmac_signature
from app.schemas.common import success
from app.schemas.webhook import WebhookIngestRequest
from app.workers.campaign_tasks import ingest_webhook_task

router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post('/ingest', status_code=202, response_model=dict)
async def ingest_webhook(payload: WebhookIngestRequest, request: Request, x_webhook_signature: str | None = Header(default=None)):
    body = await request.body()
    if not verify_hmac_signature(body, x_webhook_signature, get_settings().webhook_signing_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid webhook signature')
    ingest_webhook_task.delay(payload.event_type.value, payload.payload, request.state.trace_id)
    return success({'accepted': True, 'event_type': payload.event_type.value}, request.state.trace_id)
