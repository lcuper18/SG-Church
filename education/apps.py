"""
Education app configuration.
"""

from django.apps import AppConfig


class EducationConfig(AppConfig):
    """Configuration for the education (courses) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "education"
    verbose_name = "Education"
