"""
Notification models for SG Church.
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Model for in-app notifications.
    """

    TYPE_CHOICES = [
        ("donation_received", "Donación Recibida"),
        ("expense_created", "Gasto Creado"),
        ("expense_approved", "Gasto Aprobado"),
        ("expense_rejected", "Gasto Rechazado"),
        ("member_added", "Nuevo Miembro"),
        ("member_updated", "Miembro Actualizado"),
        ("system", "Sistema"),
    ]

    # Tenant - required for multi-tenancy
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    # User who receives the notification
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    # Notification content
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)

    # Optional link to related object
    link = models.CharField(max_length=500, blank=True, default="")

    # Related object IDs (optional)
    content_type = models.CharField(max_length=50, blank=True, default="")
    object_id = models.PositiveIntegerField(null=True, blank=True)

    # Read status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "user", "-created_at"]),
            models.Index(fields=["tenant", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    @property
    def icon(self):
        """Return icon class based on notification type."""
        icons = {
            "donation_received": "bi-heart-fill text-success",
            "expense_created": "bi-receipt text-warning",
            "expense_approved": "bi-check-circle-fill text-success",
            "expense_rejected": "bi-x-circle-fill text-danger",
            "member_added": "bi-person-plus-fill text-primary",
            "member_updated": "bi-person-fill text-info",
            "system": "bi-info-circle-fill text-secondary",
        }
        return icons.get(self.notification_type, "bi-bell-fill")


def create_notification(
    tenant,
    user,
    title: str,
    message: str,
    notification_type: str,
    link: str = "",
    content_type: str = "",
    object_id: int | None = None,
) -> "Notification":
    """
    Helper function to create a notification.
    """
    return Notification.objects.create(
        tenant=tenant,
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        content_type=content_type,
        object_id=object_id,
    )
