"""
Email service using Resend API.
"""

import logging
from typing import Any
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class ResendEmailService:
    """
    Service class for sending emails using the Resend API.
    """

    def __init__(self):
        self.api_key = getattr(settings, "RESEND_API_KEY", None)
        self.from_email = getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@sgchurch.com"
        )
        self.from_name = getattr(settings, "EMAIL_FROM_NAME", "SG Church")

    def is_configured(self) -> bool:
        """Check if Resend API is properly configured."""
        return bool(self.api_key and self.api_key.startswith("re_"))

    def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str | None = None,
        html_content: str | None = None,
        text_content: str | None = None,
        context: dict[str, Any] | None = None,
        from_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email using Resend API.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_name: Name of HTML template to render
            html_content: HTML content (alternative to template_name)
            text_content: Plain text content
            context: Context dict for template rendering
            from_name: Override default sender name

        Returns:
            Dict with 'success', 'message_id', and optional 'error' keys
        """
        if not self.is_configured():
            logger.warning("Resend API not configured, email not sent")
            return {"success": False, "error": "Resend API not configured"}

        try:
            import resend

            resend.api_key = self.api_key

            # Prepare email content
            html = html_content
            if template_name and context:
                html = render_to_string(f"emails/{template_name}.html", context)
            elif template_name:
                html = render_to_string(f"emails/{template_name}.html", {})

            # Build the email params
            params = {
                "from": f"{from_name or self.from_name} <{self.from_email}>",
                "to": to_email,
                "subject": subject,
                "html": html,
            }

            if text_content:
                params["text"] = text_content

            # Send via Resend
            response = resend.Emails.send(params)

            logger.info(f"Email sent successfully to {to_email}: {response.get('id')}")

            return {
                "success": True,
                "message_id": response.get("id", ""),
            }

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_bulk_emails(
        self,
        recipients: list[dict[str, str]],
        subject: str,
        template_name: str | None = None,
        html_content: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send bulk emails using Resend's batch API.

        Args:
            recipients: List of dicts with 'email' and 'name' keys
            subject: Email subject line
            template_name: Name of HTML template to render
            html_content: HTML content (alternative to template_name)
            context: Context dict for template rendering

        Returns:
            Dict with 'success', 'batch_id', and optional 'error' keys
        """
        if not self.is_configured():
            logger.warning("Resend API not configured, bulk email not sent")
            return {"success": False, "error": "Resend API not configured"}

        try:
            import resend

            resend.api_key = self.api_key

            # Prepare batch emails
            emails = []
            for recipient in recipients:
                html = html_content
                if template_name and context:
                    # Merge recipient-specific context
                    full_context = {
                        **(context or {}),
                        "recipient_name": recipient.get("name", ""),
                    }
                    html = render_to_string(
                        f"emails/{template_name}.html", full_context
                    )

                emails.append(
                    {
                        "from": f"{self.from_name} <{self.from_email}>",
                        "to": recipient["email"],
                        "subject": subject,
                        "html": html,
                    }
                )

            # Send batch
            response = resend.Emails.send_batch(emails)

            logger.info(f"Bulk email sent successfully: {len(recipients)} recipients")

            return {
                "success": True,
                "batch_id": response.get("id", ""),
                "sent_count": len(recipients),
            }

        except Exception as e:
            logger.error(f"Failed to send bulk email: {str(e)}")
            return {"success": False, "error": str(e)}


# Singleton instance
email_service = ResendEmailService()
