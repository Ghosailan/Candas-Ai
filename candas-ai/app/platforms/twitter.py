from datetime import datetime
from app.platforms.base import PlatformAdapter
from app.schemas.post import PostSchema, PublishResult
from app.schemas.analytics import AnalyticsSchema
from app.core.exceptions import PlatformPublishError

class TwitterAdapter(PlatformAdapter):
    platform_name = 'twitter'

    def validate_content(self, post: PostSchema) -> list[str]:
        violations = []
        if len(post.copy) > 280:
            violations.append('character_limit_exceeded')
        return violations

    async def publish(self, post: PostSchema) -> PublishResult:
        violations = self.validate_content(post)
        if violations:
            raise PlatformPublishError('Content failed platform validation', detail={'violations': violations})
        if self.settings.platform_mock_mode:
            return await self._mock_publish(post)
        token = self.settings.twitter_access_token if hasattr(self.settings, 'twitter_access_token') else None
        if not token:
            raise PlatformPublishError('twitter access token is not configured')
        # Real platform APIs differ substantially; this adapter centralizes auth/retry/logging.
        # Replace endpoint/payload with the approved production API contract for your app account.
        response = await self._request_with_retry('POST', 'https://api.twitter.com/v1/posts', headers={'Authorization': f'Bearer {token}'}, json=post.model_dump(mode='json'))
        data = response.json()
        return PublishResult(platform=post.platform, platform_post_id=str(data.get('id')), platform_post_url=str(data.get('url')), published_at=datetime.utcnow())

    async def get_analytics(self, post_id: str, since: datetime) -> AnalyticsSchema:
        if self.settings.platform_mock_mode:
            return await self._mock_analytics(post_id)
        return AnalyticsSchema(platform='twitter', post_id=post_id)
