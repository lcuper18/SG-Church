"""
Local development settings.
"""

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Development-specific settings
INSTALLED_APPS += [
    "django_extensions",
]

# Disable TenantMiddleware and debug_toolbar for local development
MIDDLEWARE = [
    m for m in MIDDLEWARE if "TenantMiddleware" not in m and "debug_toolbar" not in m
] + [
    "allauth.account.middleware.AccountMiddleware",
]

# Email to console for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow all hosts in development
CORS_ALLOW_ALL_ORIGINS = True
