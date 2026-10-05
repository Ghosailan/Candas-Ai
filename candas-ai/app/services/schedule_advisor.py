from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.agents.tools.llm_tool import extract_json, ollama_generate
from app.models.post import Post


DEFAULT_TIMEZONE = 'Asia/Riyadh'
DAY_LOOKUP = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6,
}
PLATFORM_DEFAULTS = {
    'instagram': {'weekday': (20, 0), 'weekend': (21, 0), 'reason': 'Instagram engagement is usually stronger in the evening.'},
    'facebook': {'weekday': (19, 30), 'weekend': (20, 0), 'reason': 'Facebook audiences often respond well after work hours.'},
    'tiktok': {'weekday': (20, 30), 'weekend': (21, 30), 'reason': 'TikTok discovery tends to perform better in the evening.'},
    'linkedin': {'weekday': (9, 0), 'weekend': (10, 0), 'reason': 'LinkedIn content typically performs best on weekday mornings.'},
    'twitter': {'weekday': (13, 0), 'weekend': (19, 0), 'reason': 'Short-form conversation is commonly active around midday and early evening.'},
    'youtube': {'weekday': (20, 0), 'weekend': (18, 0), 'reason': 'YouTube viewing often increases in the evening and on weekends.'},
}


def _resolve_range(
    timezone_name: str,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone_name or DEFAULT_TIMEZONE)
    start = (start_date or datetime.now(tz)).astimezone(tz)
    end = (end_date or (start + timedelta(days=7))).astimezone(tz)
    if end < start:
        end = start + timedelta(days=7)
    return start, end


def _pick_day(
    start: datetime,
    end: datetime,
    preferred_days: list[str] | None,
    index: int,
) -> datetime:
    allowed = {DAY_LOOKUP[day.strip().lower()] for day in preferred_days or [] if day.strip().lower() in DAY_LOOKUP}
    cursor = start + timedelta(days=index)
    for offset in range(max((end - start).days + 1, 7)):
        candidate = cursor + timedelta(days=offset)
        if candidate > end:
            break
        if not allowed or candidate.weekday() in allowed:
            return candidate
    return start + timedelta(days=index)


def _pick_time(platform: str, preferred_time_window: str | None, when: datetime) -> tuple[int, int]:
    defaults = PLATFORM_DEFAULTS.get(platform, PLATFORM_DEFAULTS['instagram'])
    if preferred_time_window:
        key = preferred_time_window.strip().lower()
        if key == 'morning':
            return (9, 0)
        if key == 'midday':
            return (13, 0)
        if key == 'evening':
            return (20, 0)
    return defaults['weekend'] if when.weekday() >= 5 else defaults['weekday']


def _fallback_suggestions(
    posts: list[Post],
    timezone_name: str,
    start_date: datetime | None,
    end_date: datetime | None,
    preferred_days: list[str] | None,
    preferred_time_window: str | None,
) -> list[dict]:
    start, end = _resolve_range(timezone_name, start_date, end_date)
    suggestions = []
    for index, post in enumerate(posts):
        day = _pick_day(start, end, preferred_days, index)
        hour, minute = _pick_time(post.platform.value, preferred_time_window, day)
        scheduled = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        defaults = PLATFORM_DEFAULTS.get(post.platform.value, PLATFORM_DEFAULTS['instagram'])
        suggestions.append(
            {
                'post_id': str(post.id),
                'platform': post.platform.value,
                'recommended_publish_at': scheduled.isoformat(),
                'reason': defaults['reason'],
                'confidence': 0.58,
            }
        )
    return suggestions


async def recommend_post_times(
    campaign,
    posts: list[Post],
    timezone_name: str = DEFAULT_TIMEZONE,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    preferred_days: list[str] | None = None,
    preferred_time_window: str | None = None,
) -> list[dict]:
    fallback = _fallback_suggestions(
        posts,
        timezone_name,
        start_date,
        end_date,
        preferred_days,
        preferred_time_window,
    )
    system_prompt = (
        'You recommend social media posting times. '
        'Return valid JSON only with shape {"suggestions":[{"post_id":"...","platform":"...","recommended_publish_at":"ISO8601","reason":"...","confidence":0.0}]}. '
        'Use the provided timezone in the timestamp offset. Do not include markdown.'
    )
    prompt = json.dumps(
        {
            'campaign_title': campaign.title,
            'campaign_brief': campaign.brief,
            'goals': campaign.goals,
            'target_audience': campaign.target_audience,
            'timezone': timezone_name,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'preferred_days': preferred_days or [],
            'preferred_time_window': preferred_time_window,
            'posts': [
                {
                    'post_id': str(post.id),
                    'platform': post.platform.value,
                    'copy': post.copy,
                    'image_prompt': post.image_prompt,
                }
                for post in posts
            ],
        }
    )
    try:
        raw = await ollama_generate(system_prompt, prompt, max_tokens=1800)
        data = extract_json(raw)
        suggestions = data.get('suggestions', [])
        if not isinstance(suggestions, list) or len(suggestions) != len(posts):
            return fallback
        normalized = []
        for index, item in enumerate(suggestions):
            publish_at = datetime.fromisoformat(str(item['recommended_publish_at']))
            if publish_at.tzinfo is None:
                publish_at = publish_at.replace(tzinfo=ZoneInfo(timezone_name or DEFAULT_TIMEZONE))
            normalized.append(
                {
                    'post_id': str(item.get('post_id') or posts[index].id),
                    'platform': str(item.get('platform') or posts[index].platform.value),
                    'recommended_publish_at': publish_at.isoformat(),
                    'reason': str(item.get('reason') or fallback[index]['reason']),
                    'confidence': max(0.0, min(1.0, float(item.get('confidence', fallback[index]['confidence'])))),
                }
            )
        return normalized
    except Exception:
        return fallback
