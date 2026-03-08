"""
app/workers/celery_app.py
──────────────────────────
Celery application factory.
Configured for Redis broker with production-tuned settings.
"""

from celery import Celery
from celery.signals import worker_ready

from app.config import settings
from app.utils.logging import get_logger, configure_logging

logger = get_logger(__name__)


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    app = Celery(
        "crypto_ops",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.workers.tasks"],
    )

    app.conf.update(
        # Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Timezone
        timezone="UTC",
        enable_utc=True,

        # Task behavior
        task_acks_late=True,          # Acknowledge after task completes (not before)
        task_reject_on_worker_lost=True,  # Re-queue if worker dies mid-task
        task_track_started=True,      # Track when tasks begin

        # Retry configuration
        task_max_retries=3,
        task_default_retry_delay=5,   # Seconds between retries

        # Result expiry
        result_expires=86400,         # Keep results for 24h

        # Worker configuration
        worker_prefetch_multiplier=1,  # One task at a time per worker (I/O bound AI calls)
        worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory safety)

        # Route tasks to specific queues
        task_routes={
            "app.workers.tasks.classify_ticket_task": {"queue": "classification"},
            "app.workers.tasks.fraud_scan_task": {"queue": "fraud"},
            "app.workers.tasks.route_ticket_task": {"queue": "routing"},
        },

        # Queue definitions
        task_queues={
            "classification": {"exchange": "classification", "routing_key": "classification"},
            "fraud": {"exchange": "fraud", "routing_key": "fraud"},
            "routing": {"exchange": "routing", "routing_key": "routing"},
        },
        task_default_queue="classification",
    )

    return app


# Application instance
celery_app = create_celery_app()


@worker_ready.connect
def on_worker_ready(**kwargs):
    configure_logging()
    logger.info("celery_worker_ready", broker=settings.celery_broker_url)
