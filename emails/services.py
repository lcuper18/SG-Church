"""
Sending e-mail through Django's configured backend (EMAIL_BACKEND).

SMTP works with any provider (Gmail, Brevo, Mailgun, the church's own server)
and with self-hosted installs. Without credentials the default console backend
just prints messages to the log, so nothing breaks on a fresh install or demo.
"""

import logging
import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Reserved domains that can never receive mail (RFC 2606/6761). The demo data
# uses @demo.sgchurch.test; sending there would only produce bounces.
_UNDELIVERABLE_TLDS = ("test", "invalid", "example", "localhost")
_UNDELIVERABLE_DOMAINS = ("example.com", "example.org", "example.net")


def is_deliverable(address):
    """False for empty/malformed addresses and reserved test domains."""
    if not address or "@" not in address:
        return False
    domain = address.rsplit("@", 1)[1].strip().lower()
    if "." not in domain or domain in _UNDELIVERABLE_DOMAINS:
        return False
    return domain.rsplit(".", 1)[1] not in _UNDELIVERABLE_TLDS


def render_email(template_name, context, tenant=None):
    """Render emails/<template_name>.html (and .txt) in the church's time zone
    and in Spanish, regardless of who triggered the e-mail."""
    context = {
        "church_name": tenant.name if tenant else "SG Church",
        "tenant": tenant,
        **context,
    }
    zone_name = getattr(tenant, "timezone", None) or settings.TIME_ZONE
    with timezone.override(zone_name), translation.override("es"):
        html = render_to_string(f"emails/{template_name}.html", context)
        try:
            text = render_to_string(f"emails/{template_name}.txt", context)
        except Exception:  # no .txt written for this e-mail: derive one
            text = re.sub(r"\n\s*\n+", "\n\n", strip_tags(html)).strip()
    return html, text.strip()


def send_message(to_email, subject, html, text, from_name=None, reply_to=None, headers=None):
    """Send one message. Returns {"success": bool, "error": str}; never raises."""
    from_address = settings.DEFAULT_FROM_EMAIL
    sender = f"{from_name} <{from_address}>" if from_name else from_address
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=sender,
            to=[to_email],
            reply_to=[reply_to] if reply_to else None,
            headers=headers or None,
        )
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
        return {"success": True, "error": ""}
    except Exception as error:  # SMTP down, bad credentials, rejected address...
        logger.warning("Email to %s failed: %s", to_email, error)
        return {"success": False, "error": str(error)[:500]}
