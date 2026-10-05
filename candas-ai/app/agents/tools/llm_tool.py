import asyncio
import json
import httpx
from langchain_core.tools import tool
from app.config import get_settings


async def ollama_generate(system_prompt: str, user_prompt: str, model: str | None = None, max_tokens: int = 1024) -> str:
    settings = get_settings()
    selected_model = model or settings.ollama_primary_model
    prompt = f'SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}'
    payload = {'model': selected_model, 'prompt': prompt, 'stream': False, 'options': {'num_predict': max_tokens, 'temperature': 0.2}}
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f'{settings.ollama_base_url.rstrip("/")}/api/generate', json=payload)
                response.raise_for_status()
                return response.json().get('response', '')
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code == 429:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
        except httpx.HTTPError as exc:
            last_error = exc
            payload['model'] = settings.ollama_fallback_model
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f'Ollama generation failed: {last_error}')


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`').replace('json\n', '', 1)
    start, end = cleaned.find('{'), cleaned.rfind('}')
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)

@tool('llm_tool')
def llm_tool(model: str, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Generate text using the local Ollama LLM with retry and fallback."""
    return asyncio.run(ollama_generate(system_prompt, user_prompt, model, max_tokens))
