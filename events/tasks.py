"""Celery tasks for events."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_event_reminders():
    """Beat task (every 5 minutes): queue the reminders that are due."""
    from .reminders import send_due_reminders

    queued = send_due_reminders()
    if queued:
        logger.info("Queued %s event reminder(s)", queued)
    return queued
