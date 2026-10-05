import asyncio
import mimetypes
from datetime import datetime, timezone
from urllib.parse import urlparse

import boto3
import httpx
from structlog import get_logger

from app.core.exceptions import PlatformPublishError
from app.platforms.base import PlatformAdapter
from app.schemas.analytics import AnalyticsSchema
from app.schemas.post import PostSchema, PublishResult

log = get_logger()


class TelegramAdapter(PlatformAdapter):
    platform_name = 'telegram'

    def validate_content(self, post: PostSchema) -> list[str]:
        return []

    def _config(self) -> tuple[str, str]:
        bot_token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id
        if not bot_token or not chat_id:
            raise PlatformPublishError(
                'Telegram publishing is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.',
                detail={'required': ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']},
            )
        return bot_token, chat_id

    @staticmethod
    def _telegram_post_url(chat_id: str, message_id: int | str) -> str | None:
        if not chat_id.startswith('@'):
            return None
        channel = chat_id[1:]
        return f'https://t.me/{channel}/{message_id}'

    def _should_download_s3_image(self, image_url: str) -> bool:
        public_base = self.settings.s3_public_base_url
        if public_base and image_url.startswith(public_base):
            return True
        return 'localhost:9000' in image_url

    def _parse_s3_url(self, image_url: str) -> tuple[str, str]:
        parsed = urlparse(image_url)
        path = parsed.path.lstrip('/')
        if not path:
            raise PlatformPublishError(
                'Telegram image upload failed: image URL did not include an object path.',
                detail={'image_url': image_url},
            )

        public_base = self.settings.s3_public_base_url
        if public_base and image_url.startswith(public_base):
            base_path = urlparse(public_base).path.lstrip('/')
            if not base_path:
                raise PlatformPublishError(
                    'Telegram image upload failed: S3_PUBLIC_BASE_URL is missing a bucket path.',
                    detail={'s3_public_base_url': public_base},
                )
            if path == base_path or not path.startswith(f'{base_path}/'):
                raise PlatformPublishError(
                    'Telegram image upload failed: image URL did not match S3_PUBLIC_BASE_URL.',
                    detail={'image_url': image_url},
                )
            bucket = base_path.split('/', 1)[0]
            key = path[len(base_path) + 1 :]
            if not key:
                raise PlatformPublishError(
                    'Telegram image upload failed: image URL did not include an object key.',
                    detail={'image_url': image_url},
                )
            return bucket, key

        parts = path.split('/', 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise PlatformPublishError(
                'Telegram image upload failed: image URL did not include bucket and key.',
                detail={'image_url': image_url},
            )
        return parts[0], parts[1]

    def _download_s3_image(self, image_url: str) -> tuple[bytes, str]:
        bucket, key = self._parse_s3_url(image_url)
        try:
            client = boto3.client(
                's3',
                endpoint_url=self.settings.s3_endpoint_url,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                region_name=self.settings.aws_region,
            )
            response = client.get_object(Bucket=bucket, Key=key)
            body = response['Body'].read()
        except Exception as exc:
            raise PlatformPublishError(
                'Telegram image upload failed: could not download image from S3/MinIO.',
                detail={'bucket': bucket, 'key': key},
            ) from exc
        if not body:
            raise PlatformPublishError(
                'Telegram image upload failed: downloaded image was empty.',
                detail={'bucket': bucket, 'key': key},
            )
        return body, key.rsplit('/', 1)[-1]

    async def _send(
        self,
        method: str,
        payload: dict[str, str],
        *,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        use_json: bool = True,
    ) -> dict:
        bot_token, _ = self._config()
        await self._consume_rate_token()
        url = f'https://api.telegram.org/bot{bot_token}/{method}'
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if files:
                    request_kwargs = {'files': files, 'data': payload}
                elif use_json:
                    request_kwargs = {'json': payload}
                else:
                    request_kwargs = {'data': payload}
                response = await client.post(url, **request_kwargs)
        except httpx.HTTPError as exc:
            raise PlatformPublishError(
                f'Telegram publish request failed: {exc}',
                detail={'method': method},
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise PlatformPublishError(
                'Telegram publish failed with a non-JSON response.',
                detail={'status_code': response.status_code, 'body': response.text[:500]},
            ) from exc

        if response.status_code >= 400:
            description = data.get('description') if isinstance(data, dict) else response.reason_phrase
            raise PlatformPublishError(
                f'Telegram publish failed: {description or response.reason_phrase}',
                detail={'status_code': response.status_code, 'response': data},
            )
        if not isinstance(data, dict) or not data.get('ok'):
            description = data.get('description') if isinstance(data, dict) else 'Unknown Telegram API error.'
            raise PlatformPublishError(
                f'Telegram publish failed: {description}',
                detail={'response': data},
            )
        return data

    async def _send_message(self, chat_id: str, text: str) -> dict:
        return await self._send('sendMessage', {'chat_id': chat_id, 'text': text})

    async def _send_photo(self, chat_id: str, post: PostSchema) -> dict:
        if not post.image_url:
            raise PlatformPublishError('Telegram image upload failed: post has no image URL.')

        if self._should_download_s3_image(post.image_url):
            image_bytes, filename = await asyncio.to_thread(self._download_s3_image, post.image_url)
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            return await self._send(
                'sendPhoto',
                {'chat_id': chat_id, 'caption': post.copy},
                files={'photo': (filename, image_bytes, content_type)},
                use_json=False,
            )

        return await self._send(
            'sendPhoto',
            {'chat_id': chat_id, 'photo': post.image_url, 'caption': post.copy},
        )

    async def publish(self, post: PostSchema) -> PublishResult:
        if self.settings.platform_mock_mode:
            return await self._mock_publish(post)

        _, chat_id = self._config()
        if post.image_url:
            try:
                data = await self._send_photo(chat_id, post)
            except Exception as exc:
                detail = exc.detail if isinstance(exc, PlatformPublishError) else {}
                error = exc.message if isinstance(exc, PlatformPublishError) else str(exc)
                log.warning(
                    'telegram_photo_publish_failed',
                    trace_id=self.trace_id,
                    platform=self.platform_name,
                    detail=detail,
                    error=error,
                )
                data = await self._send_message(chat_id, post.copy)
        else:
            data = await self._send_message(chat_id, post.copy)

        result = data.get('result') if isinstance(data, dict) else None
        message_id = result.get('message_id') if isinstance(result, dict) else None
        if message_id is None:
            raise PlatformPublishError(
                'Telegram publish succeeded but no message_id was returned.',
                detail={'response': data},
            )

        return PublishResult(
            platform=post.platform,
            platform_post_id=str(message_id),
            platform_post_url=self._telegram_post_url(chat_id, message_id),
            published_at=datetime.now(timezone.utc),
        )

    async def get_analytics(self, post_id: str, since: datetime) -> AnalyticsSchema:
        if self.settings.platform_mock_mode:
            return await self._mock_analytics(post_id)
        return AnalyticsSchema(platform='telegram', post_id=post_id)
