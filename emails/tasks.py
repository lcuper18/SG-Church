"""
Celery tasks for sending e-mail without blocking the request.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_logged_email_task(self, log_id, html, text, from_name=None, reply_to=None, headers=None):
    """Send the message recorded in EmailLog `log_id` (already rendered).

    Failed attempts are retried; the log shows the last outcome."""
    from emails.models import EmailLog
    from emails.services import send_message

    try:
        log = EmailLog.objects.get(pk=log_id)
    except EmailLog.DoesNotExist:
        logger.error("EmailLog %s not found", log_id)
        return {"success": False, "error": "log not found"}

    result = send_message(log.to_email, log.subject, html, text, from_name, reply_to, headers)
    log.status = "sent" if result["success"] else "failed"
    log.error_message = result["error"]
    if result["success"]:
        log.sent_at = timezone.now()
    log.save(update_fields=["status", "error_message", "sent_at"])

    if not result["success"] and self.request.retries < self.max_retries:
        raise self.retry(exc=Exception(result["error"]))
    return result


@shared_task
def send_donation_receipt_task(donation_id):
    """Receipt for a completed donation (queued by the Stripe webhook)."""
    from emails import notify
    from finance.models import Donation

    donation = (
        Donation.objects.select_related("tenant", "member").filter(pk=donation_id).first()
    )
    if donation is None:
        logger.error("Donation %s not found", donation_id)
        return {"success": False, "error": "Donation not found"}
    return {"queued": notify.donation_receipt(donation)}
