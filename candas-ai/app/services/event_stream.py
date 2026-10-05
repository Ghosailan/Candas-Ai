import json
from datetime import datetime, timezone
import redis.asyncio as redis
from app.config import get_settings


def channel_for_campaign(campaign_id: str) -> str:
    return f'campaign:{campaign_id}:events'


async def publish_event(campaign_id: str, event: str, node: str | None = None, detail: dict | None = None, trace_id: str | None = None) -> None:
    client = redis.from_url(get_settings().redis_url)
    payload = {
        'event': event,
        'node': node,
        'detail': detail or {},
        'trace_id': trace_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    await client.publish(channel_for_campaign(campaign_id), json.dumps(payload))
    await client.aclose()
