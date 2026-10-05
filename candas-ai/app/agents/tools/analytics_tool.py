from datetime import datetime, timezone
from langchain_core.tools import tool
from app.models.enums import Platform
from app.platforms import get_adapter

@tool('analytics_tool')
def analytics_tool(platform: str, post_id: str, since_iso: str | None = None) -> dict:
    """Fetch normalized analytics from a platform adapter."""
    import asyncio
    async def _run():
        since = datetime.fromisoformat(since_iso) if since_iso else datetime.now(timezone.utc)
        result = await get_adapter(Platform(platform)).get_analytics(post_id, since)
        return result.model_dump(mode='json')
    return asyncio.run(_run())
