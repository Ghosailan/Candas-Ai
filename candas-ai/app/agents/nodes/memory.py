import redis.asyncio as redis
from app.config import get_settings
from app.core.telemetry import agent_span
from app.database import get_sessionmaker
from app.services.event_stream import publish_event
from app.services.memory_service import retrieve_similar_campaigns

async def memory_node(state):
    campaign_id = state['campaign_id']; trace_id = state.get('trace_id')
    await publish_event(campaign_id, 'node_started', 'memory', trace_id=trace_id)
    with agent_span('memory'):
        settings = get_settings()
        client = redis.from_url(settings.redis_url)
        brand_key = f'brand_guidelines:{state["org_id"]}'
        cached = await client.get(brand_key)
        if cached:
            guidelines = cached.decode()
        else:
            guidelines = state.get('brand_guidelines') or 'Use clear, honest, brand-safe marketing language. Avoid unsupported claims.'
            await client.setex(brand_key, 3600, guidelines)
        await client.aclose()
        async with get_sessionmaker()() as session:
            memory = await retrieve_similar_campaigns(session, state['org_id'], state['brief'], limit=5)
        out = {'brand_guidelines': guidelines, 'memory_context': memory}
    await publish_event(campaign_id, 'node_completed', 'memory', out, trace_id=trace_id)
    return out
