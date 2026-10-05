from app.models.enums import Platform
from app.platforms.instagram import InstagramAdapter
from app.platforms.twitter import TwitterAdapter
from app.platforms.linkedin import LinkedInAdapter
from app.platforms.tiktok import TikTokAdapter
from app.platforms.facebook import FacebookAdapter
from app.platforms.telegram import TelegramAdapter
from app.platforms.youtube import YouTubeAdapter

ADAPTERS = {
    Platform.instagram: InstagramAdapter,
    Platform.twitter: TwitterAdapter,
    Platform.linkedin: LinkedInAdapter,
    Platform.tiktok: TikTokAdapter,
    Platform.facebook: FacebookAdapter,
    Platform.telegram: TelegramAdapter,
    Platform.youtube: YouTubeAdapter,
}

def get_adapter(platform: Platform, trace_id: str | None = None):
    return ADAPTERS[platform](trace_id=trace_id)
