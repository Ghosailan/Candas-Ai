from datetime import datetime, timedelta, timezone
from langchain_core.tools import tool

PLATFORM_OFFSETS = {'instagram': 18, 'facebook': 17, 'linkedin': 9, 'twitter': 12, 'tiktok': 20, 'youtube': 16}


def optimal_publish_time(platform: str, days_ahead: int = 1) -> datetime:
    now = datetime.now(timezone.utc)
    hour = PLATFORM_OFFSETS.get(platform, 12)
    target = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target

@tool('scheduler_tool')
def scheduler_tool(platform: str, target_audience: dict | None = None) -> str:
    """Return the optimal publish datetime in UTC for a platform."""
    return optimal_publish_time(platform).isoformat()
