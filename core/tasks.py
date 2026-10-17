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


@shared_task(ignore_result=True)
def purge_trash():
    """Remove for good what has sat in the trash longer than TRASH_RETENTION_DAYS."""
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from core.views import trash_models

    cutoff = timezone.now() - timedelta(days=settings.TRASH_RETENTION_DAYS)
    removed = 0
    for _label, model, _name in trash_models():
        for item in model.all_objects.filter(deleted_at__lt=cutoff):
            try:
                item.hard_delete(user=None)
                removed += 1
            except Exception:  # noqa: BLE001 - one stuck row must not stop the rest
                logger.exception("Could not purge %s %s", model._meta.label, item.pk)
    if removed:
        logger.info("Trash: %s record(s) removed for good", removed)
    return removed
