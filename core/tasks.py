"""
Scheduled jobs (see CELERY_BEAT_SCHEDULE in settings).
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def run_backup():
    """Nightly backup. Failures are logged (and reach Sentry when configured)
    rather than retried: the next night's run is the retry."""
    from core.backup import create_backup

    try:
        result = create_backup()
    except Exception:
        logger.exception("Scheduled backup failed")
        raise
    if result["upload_error"]:
        logger.error("Scheduled backup: off-site copy failed: %s", result["upload_error"])
