"""
Test settings for SG Church.

This module configures Django settings specifically for running tests.
It uses an in-memory SQLite database for fast test execution.
"""

from .base import *  # noqa: F401, F403

# Use SQLite for tests (faster than PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Debug is False for tests
DEBUG = False

# Use a test-specific secret key
SECRET_KEY = "test-secret-key-for-testing-only-do-not-use-in-production"

# Test email backend (prints to console)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable caching during tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Password hashers - use fast hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Faster session engine
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# Test runner settings
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Allow all hosts during tests
ALLOWED_HOSTS = ["*"]

# CORS for testing
CORS_ALLOW_ALL_ORIGINS = True

# Celery - use synchronous mode for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Rest Framework test settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# Media files
MEDIA_ROOT = "/tmp/test_media"

# File storage
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_URL = "/media/"

# Disable debug toolbar in tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]

MIDDLEWARE = [
    middleware for middleware in MIDDLEWARE if "debug_toolbar" not in middleware
] + [
    "allauth.account.middleware.AccountMiddleware",
]
