"""Celery tasks for events."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_event_reminders():
    """Beat task (every 5 minutes): queue the reminders that are due."""
    from .reminders import send_due_reminders

    from .announcements import send_due

    queued = send_due_reminders()
    if queued:
        logger.info("Queued %s event reminder(s)", queued)
    send_due()  # custom announcements that are due
    return queued


@shared_task
def send_event_announcements():
    """Send the custom announcements that are due (called right after one is created)."""
    from .announcements import send_due

    return send_due()
