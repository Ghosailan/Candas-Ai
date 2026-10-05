from celery import Celery
from celery.schedules import crontab

from app.config import Settings

settings = Settings()

redis_url = str(settings.redis_url)

celery_app = Celery(
    "agentic_campaign_manager",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.workers.campaign_tasks",
        "app.workers.analytics_tasks",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={
        "publish-due-posts-every-minute": {
            "task": "publish_due_posts_task",
            "schedule": crontab(minute="*"),
        }
    },
)
