"""
Local development settings.
"""

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Development-specific settings
INSTALLED_APPS += [
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Django Debug Toolbar
INTERNAL_IPS = [
    "127.0.0.1",
]

# Email to console for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow all hosts in development
CORS_ALLOW_ALL_ORIGINS = True
