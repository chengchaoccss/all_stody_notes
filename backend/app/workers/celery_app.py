from celery import Celery

from app.config import settings

celery_app = Celery(
    "video_to_notes",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.pipeline"],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=60 * 60 * 3,
    task_soft_time_limit=60 * 60 * 2,
    timezone="Asia/Shanghai",
)
