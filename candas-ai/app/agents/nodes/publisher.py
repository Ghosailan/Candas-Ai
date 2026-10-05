from app.core.telemetry import agent_span
from app.services.event_stream import publish_event


async def publisher_node(state):
    # Import inside the node to avoid circular import:
    # campaign_tasks -> graph -> publisher_node -> campaign_tasks
    from app.workers.campaign_tasks import publish_post_task

    campaign_id = state["campaign_id"]
    trace_id = state.get("trace_id")

    await publish_event(campaign_id, "node_started", "publisher", trace_id=trace_id)

    with agent_span("publisher"):
        ids = []

        for item in state.get("schedule", []):
            ids.append(item["post_id"])
            publish_post_task.delay(item["post_id"], item["publish_at"], trace_id)

        out = {"published_post_ids": ids}

    await publish_event(
        campaign_id,
        "node_completed",
        "publisher",
        {"queued": len(ids)},
        trace_id=trace_id,
    )

    return out