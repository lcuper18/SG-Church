"""
Email models for SG Church.
"""

from django.db import models
from django.conf import settings


class EmailLog(models.Model):
    """
    Model to log all emails sent through the system.
    Used for auditing and debugging email delivery.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("bounced", "Bounced"),
    ]

    # Tenant (nullable for system emails)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_logs",
    )

    # Email recipients
    to_email = models.EmailField()
    to_name = models.CharField(max_length=255, blank=True, default="")
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True, default="")

    # Email content
    subject = models.CharField(max_length=500)
    template_name = models.CharField(max_length=100, blank=True, default="")
    context = models.JSONField(default=dict, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, default="")

    # Resend integration
    resend_message_id = models.CharField(max_length=100, blank=True, default="")

    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["to_email", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Email to {self.to_email}: {self.subject}"
