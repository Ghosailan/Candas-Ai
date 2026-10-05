from datetime import datetime, timezone

import httpx

from app.core.exceptions import PlatformPublishError
from app.platforms.base import PlatformAdapter
from app.schemas.analytics import AnalyticsSchema
from app.schemas.post import PostSchema, PublishResult


class FacebookAdapter(PlatformAdapter):
    platform_name = 'facebook'

    def validate_content(self, post: PostSchema) -> list[str]:
        violations = []
        if len(post.copy) > 63206:
            violations.append('character_limit_exceeded')
        return violations

    def _graph_url(self, endpoint: str) -> str:
        graph_version = self.settings.meta_graph_version
        page_id = self.settings.facebook_page_id
        if not graph_version:
            raise PlatformPublishError('META_GRAPH_VERSION is not configured.')
        if not page_id:
            raise PlatformPublishError('FACEBOOK_PAGE_ID is not configured.')
        return f'https://graph.facebook.com/{graph_version}/{page_id}/{endpoint}'

    def _page_access_token(self) -> str:
        token = self.settings.facebook_page_access_token or self.settings.facebook_access_token
        if not token:
            raise PlatformPublishError(
                'FACEBOOK_PAGE_ACCESS_TOKEN is not configured.',
                detail={'required': ['FACEBOOK_PAGE_ACCESS_TOKEN']},
            )
        return token

    @staticmethod
    def _facebook_post_url(post_id: str) -> str:
        return f'https://www.facebook.com/{post_id}'

    @staticmethod
    def _extract_meta_error(payload: dict | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        error = payload.get('error')
        if not isinstance(error, dict):
            return None
        message = error.get('message') or 'Meta Graph API returned an unknown error.'
        code = error.get('code')
        subcode = error.get('error_subcode')
        parts = [str(message)]
        if code is not None:
            parts.append(f'code={code}')
        if subcode is not None:
            parts.append(f'subcode={subcode}')
        return ' '.join(parts)

    async def _post_to_meta(self, endpoint: str, payload: dict[str, str]) -> dict:
        await self._consume_rate_token()
        url = self._graph_url(endpoint)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, data=payload)
        except httpx.HTTPError as exc:
            raise PlatformPublishError(
                f'Facebook publish request failed: {exc}',
                detail={'endpoint': endpoint},
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise PlatformPublishError(
                'Facebook publish failed with a non-JSON response.',
                detail={'status_code': response.status_code, 'body': response.text[:500]},
            ) from exc

        meta_error = self._extract_meta_error(data)
        if response.status_code >= 400 or meta_error:
            raise PlatformPublishError(
                f'Facebook publish failed: {meta_error or response.reason_phrase}',
                detail={
                    'status_code': response.status_code,
                    'endpoint': endpoint,
                    'response': data,
                },
            )
        return data

    async def publish(self, post: PostSchema) -> PublishResult:
        violations = self.validate_content(post)
        if violations:
            raise PlatformPublishError('Content failed platform validation', detail={'violations': violations})
        if self.settings.platform_mock_mode:
            return await self._mock_publish(post)

        access_token = self._page_access_token()
        endpoint = 'photos' if post.image_url else 'feed'
        payload = {'access_token': access_token}
        if post.image_url:
            payload['url'] = post.image_url
            payload['caption'] = post.copy
        else:
            payload['message'] = post.copy

        data = await self._post_to_meta(endpoint, payload)
        post_id = data.get('id')
        if not post_id:
            raise PlatformPublishError(
                'Facebook publish succeeded but Meta did not return a post id.',
                detail={'endpoint': endpoint, 'response': data},
            )
        post_id = str(post_id)
        return PublishResult(
            platform=post.platform,
            platform_post_id=post_id,
            platform_post_url=self._facebook_post_url(post_id),
            published_at=datetime.now(timezone.utc),
        )

    async def get_analytics(self, post_id: str, since: datetime) -> AnalyticsSchema:
        if self.settings.platform_mock_mode:
            return await self._mock_analytics(post_id)
        return AnalyticsSchema(platform='facebook', post_id=post_id)
