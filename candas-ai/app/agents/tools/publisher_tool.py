from datetime import datetime
from langchain_core.tools import tool
from app.models.enums import Platform
from app.platforms import get_adapter
from app.schemas.post import PostSchema

@tool('publisher_tool')
def publisher_tool(post: dict, trace_id: str | None = None) -> dict:
    """Publish a social post through the correct platform adapter."""
    import asyncio
    async def _run():
        post_schema = PostSchema(**post)
        adapter = get_adapter(Platform(post_schema.platform), trace_id=trace_id)
        result = await adapter.publish(post_schema)
        return result.model_dump(mode='json')
    return asyncio.run(_run())
