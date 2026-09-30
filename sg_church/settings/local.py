"""
Local development settings.
"""

import os

# Dev-only fallback so `runserver` works without an .env file. Never used in
# production: production.py/standalone.py require a real SECRET_KEY.
os.environ.setdefault("SECRET_KEY", "local-dev-only-insecure-key-do-not-deploy")

from .base import *  # noqa: E402,F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Development-specific settings
INSTALLED_APPS += [
    "django_extensions",
]

# Email to console for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow all hosts in development
CORS_ALLOW_ALL_ORIGINS = True
