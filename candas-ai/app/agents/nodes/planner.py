from app.agents.tools.llm_tool import ollama_generate, extract_json
from app.core.telemetry import agent_span
from app.services.event_stream import publish_event

SYSTEM = 'You are a senior marketing strategist. Given the campaign brief and goals, produce valid JSON with keys: goals (list), target_audience (object), plan (object with number_of_posts_per_platform, content_themes, key_messages, call_to_action, tone). Do not add markdown.'

async def planner_node(state):
    campaign_id = state['campaign_id']; trace_id = state.get('trace_id')
    await publish_event(campaign_id, 'node_started', 'planner', trace_id=trace_id)
    with agent_span('planner'):
        prompt = f"Brief: {state['brief']}\nPlatforms: {state['platforms']}\nBrand guidelines: {state.get('brand_guidelines','')}\nMemory: {state.get('memory_context','')}"
        try:
            data = extract_json(await ollama_generate(SYSTEM, prompt, max_tokens=1000))
        except Exception:
            data = {'goals': state.get('goals') or ['awareness'], 'target_audience': state.get('target_audience') or {'segment': 'general'}, 'plan': {'tone': 'professional', 'call_to_action': 'Learn more'}}
        out = {'goals': data.get('goals', []), 'target_audience': data.get('target_audience', {}), 'messages': [{'role':'assistant','content': str(data)}]}
    await publish_event(campaign_id, 'node_completed', 'planner', out, trace_id=trace_id)
    return out
