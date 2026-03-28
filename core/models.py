"""
Core models for SG Church.
Base models and utilities used across the application.
"""

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
