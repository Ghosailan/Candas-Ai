from app.core.telemetry import agent_span
from app.services.event_stream import publish_event

async def researcher_node(state):
    campaign_id = state['campaign_id']; trace_id = state.get('trace_id')
    await publish_event(campaign_id, 'node_started', 'researcher', trace_id=trace_id)
    with agent_span('researcher'):
        context = '\n'.join([
            'Brand memory:', state.get('memory_context',''),
            'Audience:', str(state.get('target_audience', {})),
            'Historical analytics: use platform-specific strongest hours and proven CTA patterns.',
        ])
        out = {'research_context': context}
    await publish_event(campaign_id, 'node_completed', 'researcher', {'context_chars': len(context)}, trace_id=trace_id)
    return out
