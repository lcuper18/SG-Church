"""
The e-mails the system sends. Each function builds the message and queues it;
none of them ever raises, so a mail problem can't break the action that
triggered it (registering someone, completing a course, a Stripe webhook...).
"""

import logging

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .models import EmailLog
from .services import is_deliverable, render_email, send_message

logger = logging.getLogger(__name__)


def _site_url(request=None):
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    return getattr(settings, "SITE_URL", "").rstrip("/")


def queue_email(to_email, subject, template, context, tenant=None):
    """Render and queue one e-mail. Returns True if it was queued/sent."""
    try:
        if not is_deliverable(to_email):
            logger.info("Skipping email to undeliverable address %r", to_email)
            return False

        html, text = render_email(template, context, tenant)
        from_name = tenant.name if tenant else "SG Church"
        reply_to = getattr(tenant, "email", "") or None
        log = EmailLog.objects.create(
            tenant=tenant,
            to_email=to_email,
            from_email=settings.DEFAULT_FROM_EMAIL,
            from_name=from_name,
            subject=subject,
            template_name=template,
        )

        from .tasks import send_logged_email_task

        try:
            send_logged_email_task.delay(log.pk, html, text, from_name, reply_to)
        except Exception as error:  # broker down: send right away instead
            logger.warning("Celery unavailable (%s); sending %s inline", error, to_email)
            result = send_message(to_email, subject, html, text, from_name, reply_to)
            log.status = "sent" if result["success"] else "failed"
            log.error_message = result["error"]
            log.sent_at = timezone.now() if result["success"] else None
            log.save()
        return True
    except Exception:
        logger.exception("Could not queue email %r to %r", template, to_email)
        return False


def account_created(user, request=None):
    """Tell a new user their account exists, with a link to choose their own
    password (the password the admin typed is never e-mailed)."""
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import user_pk_to_url_str

    try:
        key = default_token_generator.make_token(user)
        path = reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": user_pk_to_url_str(user), "key": key},
        )
    except Exception:
        logger.exception("Could not build the password link for %s", user.email)
        path = ""
    site = _site_url(request)
    tenant = user.tenant
    return queue_email(
        user.email,
        f"Tu cuenta en {tenant.name if tenant else 'SG Church'}",
        "account_created",
        {
            "user": user,
            "role": user.get_role_display(),
            "login_url": f"{site}{reverse('login')}" if site else "",
            "password_url": f"{site}{path}" if site and path else "",
        },
        tenant,
    )


def event_registration(registration, request=None):
    member, event = registration.member, registration.event
    site = _site_url(request)
    return queue_email(
        member.email,
        f"Inscripción confirmada: {event.title}",
        "event_registration",
        {
            "member": member,
            "event": event,
            "event_url": f"{site}{reverse('event_detail', args=[event.pk])}" if site else "",
        },
        event.tenant,
    )


def course_enrollment(enrollment, request=None):
    member, course = enrollment.member, enrollment.course
    site = _site_url(request)
    return queue_email(
        member.email,
        f"Inscripción confirmada: {course.title}",
        "course_enrollment",
        {
            "member": member,
            "course": course,
            "course_url": f"{site}{reverse('course_detail', args=[course.pk])}" if site else "",
        },
        course.tenant,
    )


def certificate_issued(certificate, request=None):
    member, block = certificate.member, certificate.course_block
    site = _site_url(request)
    url = reverse("block_certificate_detail", args=[certificate.pk])
    return queue_email(
        member.email,
        f"Tu certificado: {block.name}",
        "certificate_issued",
        {
            "member": member,
            "block": block,
            "certificate": certificate,
            "certificate_url": f"{site}{url}" if site else "",
        },
        block.tenant,
    )


def donation_receipt(donation):
    """Receipt for a completed donation, to the donor's e-mail (or their
    member record's). Marks the donation as receipted once queued."""
    to_email = donation.donor_email or (donation.member.email if donation.member else "")
    donor_name = donation.member.full_name if donation.member else donation.donor_name
    queued = queue_email(
        to_email,
        f"Recibo de donación - {donation.tenant.name}",
        "donation_receipt",
        {"donation": donation, "donor_name": donor_name},
        donation.tenant,
    )
    if queued:
        donation.receipt_sent = True
        donation.receipt_sent_at = timezone.now()
        donation.save(update_fields=["receipt_sent", "receipt_sent_at"])
    return queued
