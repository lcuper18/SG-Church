# SG Church Django Project

# Load the Celery app when Django starts so that @shared_task (and its
# `.delay()`) use our broker and settings -- including CELERY_TASK_ALWAYS_EAGER
# in tests and standalone installs -- instead of Celery's default AMQP-on-
# localhost app.
from .celery import app as celery_app

__all__ = ("celery_app",)
