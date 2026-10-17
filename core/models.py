"""
Core models for SG Church.
Base models and utilities used across the application.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating
    created and modified fields.
    """

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class TenantAwareModel(models.Model):
    """
    Abstract base class for models that belong to a tenant.
    Requires a 'tenant' ForeignKey field.
    """

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """One line of the audit trail (see core.audit)."""

    ACTION_CHOICES = [
        ("create", "Creó"),
        ("update", "Modificó"),
        ("delete", "Envió a la papelera"),
        ("restore", "Restauró"),
        ("purge", "Eliminó definitivamente"),
        ("import", "Importó"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="audit_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Kept apart from `user` so the entry still says who did it after the
    # account is deleted.
    user_label = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_label = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255, blank=True)
    # {"field": [old, new]} for updates.
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["tenant", "model_label", "object_id"]),
        ]

    def __str__(self):
        return f"{self.user_label} {self.action} {self.model_label} {self.object_repr}"
