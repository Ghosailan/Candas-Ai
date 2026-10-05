import uuid
from app.agents.tools.scheduler_tool import optimal_publish_time
from app.core.telemetry import agent_span
from app.services.event_stream import publish_event

async def scheduler_node(state):
    campaign_id = state['campaign_id']; trace_id = state.get('trace_id')
    await publish_event(campaign_id, 'node_started', 'scheduler', trace_id=trace_id)
    with agent_span('scheduler'):
        schedule = []
        for idx, draft in enumerate(state.get('post_drafts', []), start=1):
            schedule.append({'post_id': draft.get('id') or str(uuid.uuid4()), 'platform': draft['platform'], 'publish_at': optimal_publish_time(draft['platform'], idx).isoformat(), 'draft': draft})
        out = {'schedule': schedule}
    await publish_event(campaign_id, 'node_completed', 'scheduler', {'scheduled': len(schedule)}, trace_id=trace_id)
    return out
