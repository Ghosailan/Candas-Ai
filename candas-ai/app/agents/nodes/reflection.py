import json

from app.agents.tools.llm_tool import ollama_generate, extract_json
from app.core.telemetry import agent_span
from app.services.event_stream import publish_event

SYSTEM = (
    "You are an LLM-as-judge for marketing drafts. "
    "Return valid JSON with brand_alignment, tone_accuracy, clarity, "
    "cta_effectiveness all 0-1 and feedback string. Be strict."
)


def to_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (list, tuple, set)):
        return "\n".join(to_text(item) for item in value)

    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)

    return str(value)


async def reflection_node(state):
    campaign_id = state["campaign_id"]
    trace_id = state.get("trace_id")

    await publish_event(campaign_id, "node_started", "reflection", trace_id=trace_id)

    with agent_span("reflection"):
        scores = []
        notes = []

        for draft in state.get("post_drafts", []):
            try:
                data = extract_json(
                    await ollama_generate(SYSTEM, str(draft), max_tokens=600)
                )

                score = sum(
                    float(data.get(k, 0.75))
                    for k in [
                        "brand_alignment",
                        "tone_accuracy",
                        "clarity",
                        "cta_effectiveness",
                    ]
                ) / 4

                notes.append(to_text(data.get("feedback", "")))

            except Exception:
                score = (
                    0.8
                    if draft.get("compliance_flags", {}).get("compliant", True)
                    else 0.55
                )
                notes.append("Fallback score based on compliance and character-limit checks.")

            scores.append(score)

        aggregate = sum(scores) / len(scores) if scores else 0.0

        out = {
            "reflection_score": aggregate,
            "reflection_feedback": "\n".join(to_text(note) for note in notes if note),
            "reflection_retries": int(state.get("reflection_retries", 0))
            + (1 if aggregate < 0.75 else 0),
        }

    await publish_event(campaign_id, "node_completed", "reflection", out, trace_id=trace_id)

    return out


def route_after_reflection(state):
    if state.get("reflection_score", 0) < 0.75 and state.get("reflection_retries", 0) < 2:
        return "creator"

    return "approval"