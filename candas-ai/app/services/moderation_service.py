from dataclasses import dataclass
import httpx
from app.config import get_settings

@dataclass
class ModerationResult:
    flagged: bool
    categories: list[str]

INTERNAL_BLOCKLIST = {'guaranteed cure', 'get rich quick', 'hate speech', 'illegal weapon'}

async def moderate_text(text: str) -> ModerationResult:
    settings = get_settings()
    if settings.moderation_provider == 'openai' and settings.openai_api_key:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                'https://api.openai.com/v1/moderations',
                headers={'Authorization': f'Bearer {settings.openai_api_key}'},
                json={'model': 'omni-moderation-latest', 'input': text},
            )
            response.raise_for_status()
            result = response.json()['results'][0]
            categories = [k for k, v in result.get('categories', {}).items() if v]
            return ModerationResult(flagged=bool(result.get('flagged')), categories=categories)
    lowered = text.lower()
    categories = [term for term in INTERNAL_BLOCKLIST if term in lowered]
    return ModerationResult(flagged=bool(categories), categories=categories)
