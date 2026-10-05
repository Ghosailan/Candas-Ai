import asyncio
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import httpx
import redis.asyncio as redis
from structlog import get_logger
from app.config import get_settings
from app.core.exceptions import PlatformPublishError
from app.schemas.post import PostSchema, PublishResult
from app.schemas.analytics import AnalyticsSchema

log = get_logger()

class PlatformAdapter(ABC):
    platform_name: str
    rate_limit_per_minute: int = 60

    def __init__(self, trace_id: str | None = None):
        self.settings = get_settings()
        self.trace_id = trace_id

    @abstractmethod
    async def publish(self, post: PostSchema) -> PublishResult: ...

    @abstractmethod
    async def get_analytics(self, post_id: str, since: datetime) -> AnalyticsSchema: ...

    @abstractmethod
    def validate_content(self, post: PostSchema) -> list[str]: ...

    async def _consume_rate_token(self) -> None:
        client = redis.from_url(self.settings.redis_url)
        key = f'rate:{self.platform_name}:{int(time.time() // 60)}'
        count = await client.incr(key)
        await client.expire(key, 90)
        await client.aclose()
        if count > self.rate_limit_per_minute:
            raise PlatformPublishError(f'{self.platform_name} rate limit exceeded')

    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        await self._consume_rate_token()
        last_error: Exception | None = None
        for attempt in range(5):
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.request(method, url, **kwargs)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                log.info('platform_api_call', trace_id=self.trace_id, platform=self.platform_name, endpoint=url, status_code=response.status_code, latency_ms=latency_ms)
                if response.status_code in {429, 500, 502, 503, 504}:
                    await asyncio.sleep((2 ** attempt) + random.random())
                    continue
                response.raise_for_status()
                return response
            except Exception as exc:
                last_error = exc
                await asyncio.sleep((2 ** attempt) + random.random())
        raise PlatformPublishError(f'{self.platform_name} API failed', detail={'error': str(last_error)})

    async def _mock_publish(self, post: PostSchema) -> PublishResult:
        return PublishResult(platform=post.platform, platform_post_id=f'mock-{self.platform_name}-{int(time.time())}', platform_post_url=f'https://example.com/{self.platform_name}/mock', published_at=datetime.now(timezone.utc))

    async def _mock_analytics(self, post_id: str) -> AnalyticsSchema:
        return AnalyticsSchema(platform=self.platform_name, post_id=post_id, impressions=1000, clicks=57, reach=880, engagement_rate=0.071, conversions=5, fetched_at=datetime.now(timezone.utc))
