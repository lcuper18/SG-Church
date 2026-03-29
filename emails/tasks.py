"""
Celery tasks for sending emails asynchronously.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    template_name: str | None = None,
    html_content: str | None = None,
    text_content: str | None = None,
    context: dict | None = None,
    tenant_id: int | None = None,
    from_name: str | None = None,
    log_id: int | None = None,
):
    """
    Task to send an email asynchronously.

    Args:
        to_email: Recipient email address
        subject: Email subject
        template_name: Template name (without extension)
        html_content: HTML content (alternative to template)
        text_content: Plain text content
        context: Template context dict
        tenant_id: Optional tenant ID for logging
        from_name: Optional sender name override
        log_id: Optional EmailLog ID to update
    """
    from emails.models import EmailLog
    from emails.services import email_service

    # Update log status to pending if exists
    email_log = None
    if log_id:
        try:
            email_log = EmailLog.objects.get(id=log_id)
            email_log.status = "pending"
            email_log.save()
        except EmailLog.DoesNotExist:
            pass

    # Send the email
    result = email_service.send_email(
        to_email=to_email,
        subject=subject,
        template_name=template_name,
        html_content=html_content,
        text_content=text_content,
        context=context,
        from_name=from_name,
    )

    # Update log with result
    if email_log:
        email_log.status = "sent" if result["success"] else "failed"
        email_log.error_message = result.get("error", "")
        email_log.resend_message_id = result.get("message_id", "")
        if result["success"]:
            email_log.sent_at = timezone.now()
        email_log.save()

    # Handle retry on failure
    if not result["success"]:
        logger.warning(f"Email send failed, retrying: {to_email}")
        raise self.retry(exc=Exception(result.get("error", "Unknown error")))

    return result


@shared_task
def send_bulk_emails_task(
    recipients: list[dict],
    subject: str,
    template_name: str | None = None,
    html_content: str | None = None,
    context: dict | None = None,
    tenant_id: int | None = None,
):
    """
    Task to send bulk emails asynchronously.

    Args:
        recipients: List of dicts with 'email' and 'name' keys
        subject: Email subject
        template_name: Template name (without extension)
        html_content: HTML content (alternative to template)
        context: Template context dict
        tenant_id: Optional tenant ID for logging
    """
    from emails.services import email_service

    result = email_service.send_bulk_emails(
        recipients=recipients,
        subject=subject,
        template_name=template_name,
        html_content=html_content,
        context=context,
    )

    return result


@shared_task
def send_welcome_email_task(member_id: int):
    """
    Task to send welcome email to a new member.
    """
    from emails.services import email_service
    from members.models import Member

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        logger.error(f"Member {member_id} not found")
        return {"success": False, "error": "Member not found"}

    # Get tenant church name
    church_name = member.tenant.name if member.tenant else "SG Church"

    result = email_service.send_email(
        to_email=member.email,
        subject=f"Bienvenido a {church_name}!",
        template_name="welcome",
        context={
            "member": member,
            "church_name": church_name,
            "tenant": member.tenant,
        },
    )

    return result


@shared_task
def send_donation_receipt_task(donation_id: int):
    """
    Task to send donation receipt email.
    """
    from emails.services import email_service
    from finance.models import Donation

    try:
        donation = Donation.objects.select_related("tenant").get(id=donation_id)
    except Donation.DoesNotExist:
        logger.error(f"Donation {donation_id} not found")
        return {"success": False, "error": "Donation not found"}

    # Get donor email
    to_email = donation.donor_email or (
        donation.member.email if donation.member else None
    )
    if not to_email:
        logger.error(f"No email found for donation {donation_id}")
        return {"success": False, "error": "No recipient email"}

    # Get donor name
    donor_name = donation.donor_name
    if donation.member:
        donor_name = donation.member.full_name

    result = email_service.send_email(
        to_email=to_email,
        subject=f"Recibo de donación - {donation.tenant.name}",
        template_name="donation_receipt",
        context={
            "donation": donation,
            "donor_name": donor_name,
            "church_name": donation.tenant.name,
        },
    )

    return result
