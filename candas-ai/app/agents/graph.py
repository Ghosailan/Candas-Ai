from langgraph.graph import END, START, StateGraph
try:
    from langgraph.checkpoint.memory import MemorySaver
except Exception:  # pragma: no cover
    MemorySaver = None
try:
    from langgraph.types import interrupt
except Exception:  # pragma: no cover
    def interrupt(value):
        return value

from app.agents.state import CampaignState
from app.agents.nodes.memory import memory_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.researcher import researcher_node
from app.agents.nodes.creator import creator_node
from app.agents.nodes.reflection import reflection_node, route_after_reflection
from app.agents.nodes.scheduler import scheduler_node
from app.agents.nodes.publisher import publisher_node
from app.agents.nodes.analyst import analyst_node

async def approval_interrupt_node(state: CampaignState):
    if state.get('approval_status') == 'approved':
        return state
    decision = interrupt({'type': 'approval_required', 'campaign_id': state['campaign_id'], 'drafts': state.get('post_drafts', [])})
    if isinstance(decision, dict):
        return {'approval_status': decision.get('decision', 'pending'), 'reviewer_feedback': decision.get('feedback', '')}
    return {'approval_status': 'pending'}


def build_campaign_graph():
    workflow = StateGraph(CampaignState)
    workflow.add_node('memory', memory_node)
    workflow.add_node('planner', planner_node)
    workflow.add_node('researcher', researcher_node)
    workflow.add_node('creator', creator_node)
    workflow.add_node('reflection', reflection_node)
    workflow.add_node('approval', approval_interrupt_node)
    workflow.add_node('scheduler', scheduler_node)
    workflow.add_node('publisher', publisher_node)
    workflow.add_node('analyst', analyst_node)

    workflow.add_edge(START, 'memory')
    workflow.add_edge('memory', 'planner')
    workflow.add_edge('planner', 'researcher')
    workflow.add_edge('researcher', 'creator')
    workflow.add_edge('creator', 'reflection')
    workflow.add_conditional_edges('reflection', route_after_reflection, {'creator': 'creator', 'approval': 'approval'})
    workflow.add_edge('approval', 'scheduler')
    workflow.add_edge('scheduler', 'publisher')
    workflow.add_edge('publisher', 'analyst')
    workflow.add_edge('analyst', END)
    checkpointer = MemorySaver() if MemorySaver else None
    return workflow.compile(checkpointer=checkpointer)

graph = build_campaign_graph()
