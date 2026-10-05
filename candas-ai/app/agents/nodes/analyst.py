from app.core.telemetry import agent_span
from app.database import get_sessionmaker
from app.services.event_stream import publish_event
from app.services.memory_service import write_campaign_memory

async def analyst_node(state):
    campaign_id = state['campaign_id']; trace_id = state.get('trace_id')
    await publish_event(campaign_id, 'node_started', 'analyst', trace_id=trace_id)
    with agent_span('analyst'):
        summary = {'queued_posts': len(state.get('published_post_ids', [])), 'status': 'analytics_pending_24h_after_publish'}
        async with get_sessionmaker()() as session:
            await write_campaign_memory(session, state['org_id'], campaign_id, f"Brief: {state['brief']}\nSummary: {summary}")
            await session.commit()
        out = {'analytics_summary': summary}
    await publish_event(campaign_id, 'node_completed', 'analyst', summary, trace_id=trace_id)
    return out
