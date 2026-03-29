"""
Emails app configuration.
"""

from django.apps import AppConfig


class EmailsConfig(AppConfig):
    """Configuration for the emails app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "emails"
    verbose_name = "Email Notifications"
