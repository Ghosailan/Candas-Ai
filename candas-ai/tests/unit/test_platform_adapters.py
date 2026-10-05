from types import SimpleNamespace

import pytest
from app.models.enums import Platform
from app.platforms.instagram import InstagramAdapter
from app.platforms.telegram import TelegramAdapter
from app.core.exceptions import PlatformPublishError
from app.schemas.post import PostSchema


@pytest.mark.anyio
async def test_mock_publish():
    result = await InstagramAdapter().publish(PostSchema(platform=Platform.instagram, copy='Hello', image_url='https://x.test/a.png'))
    assert result.platform == Platform.instagram
    assert result.platform_post_id.startswith('mock-')


@pytest.mark.anyio
async def test_telegram_publish_uploads_downloaded_s3_bytes(monkeypatch):
    adapter = TelegramAdapter()
    adapter.settings = SimpleNamespace(
        platform_mock_mode=False,
        telegram_bot_token='token',
        telegram_chat_id='@channel_name',
        s3_public_base_url='http://localhost:9000/campaign-assets',
        s3_endpoint_url='http://minio:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        aws_region='us-east-1',
    )

    async def consume_rate_token():
        return None

    calls = []

    def download_s3_image(image_url: str):
        assert image_url == 'http://localhost:9000/campaign-assets/generated/file.png'
        return b'image-bytes', 'file.png'

    async def send(method, payload, *, files=None, use_json=True):
        calls.append((method, payload, files, use_json))
        return {'ok': True, 'result': {'message_id': 42}}

    monkeypatch.setattr(adapter, '_consume_rate_token', consume_rate_token)
    monkeypatch.setattr(adapter, '_download_s3_image', download_s3_image)
    monkeypatch.setattr(adapter, '_send', send)

    result = await adapter.publish(
        PostSchema(
            platform=Platform.telegram,
            copy='Hello Telegram',
            image_url='http://localhost:9000/campaign-assets/generated/file.png',
        )
    )

    assert result.platform_post_id == '42'
    assert result.platform_post_url == 'https://t.me/channel_name/42'
    assert calls == [
        (
            'sendPhoto',
            {'chat_id': '@channel_name', 'caption': 'Hello Telegram'},
            {'photo': ('file.png', b'image-bytes', 'image/png')},
            False,
        )
    ]


@pytest.mark.anyio
async def test_telegram_publish_falls_back_to_send_message_when_photo_fails(monkeypatch):
    adapter = TelegramAdapter()
    adapter.settings = SimpleNamespace(
        platform_mock_mode=False,
        telegram_bot_token='token',
        telegram_chat_id='@channel_name',
        s3_public_base_url='http://localhost:9000/campaign-assets',
        s3_endpoint_url='http://minio:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        aws_region='us-east-1',
    )

    async def send_photo(chat_id, post):
        raise PlatformPublishError('sendPhoto failed', detail={'method': 'sendPhoto'})

    async def send_message(chat_id, text):
        assert chat_id == '@channel_name'
        assert text == 'Fallback copy'
        return {'ok': True, 'result': {'message_id': 77}}

    monkeypatch.setattr(adapter, '_send_photo', send_photo)
    monkeypatch.setattr(adapter, '_send_message', send_message)

    result = await adapter.publish(
        PostSchema(
            platform=Platform.telegram,
            copy='Fallback copy',
            image_url='https://cdn.example.com/image.png',
        )
    )

    assert result.platform_post_id == '77'
    assert result.platform_post_url == 'https://t.me/channel_name/77'
