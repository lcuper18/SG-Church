"""
Standalone settings for SG Church — one church, one install, no external
services required.

Intended for a single church running the app on their own computer/small
server: SQLite instead of Postgres, Celery in synchronous ("eager") mode
instead of Redis, and no subdomain routing (TenantMiddleware falls back to
"the only tenant" automatically — see tenants/middleware.py).

For a hosted, multi-church SaaS deployment use production.py instead.
"""

import os
import secrets
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_secret_key_file = _BASE_DIR / ".django_secret_key"

# A standalone install has no one available to set environment variables by
# hand, so generate a real SECRET_KEY on first run and persist it locally
# instead of falling back to an insecure hardcoded value.
if "SECRET_KEY" not in os.environ:
    if _secret_key_file.exists():
        os.environ["SECRET_KEY"] = _secret_key_file.read_text().strip()
    else:
        generated_key = secrets.token_urlsafe(50)
        _secret_key_file.write_text(generated_key)
        os.environ["SECRET_KEY"] = generated_key

# base.py's DATABASES block requires DATABASE_PASSWORD even though it's
# overridden with SQLite below.
os.environ.setdefault("DATABASE_PASSWORD", "unused-with-sqlite")

from .base import *  # noqa: E402,F401,F403

import dj_database_url  # noqa: E402
from django.db.backends.signals import connection_created  # noqa: E402

DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", f"sqlite:///{_BASE_DIR / 'db.sqlite3'}")
    )
}


def _enable_sqlite_wal(sender, connection, **kwargs):
    """WAL mode lets reads keep working while a write is in progress."""
    if connection.vendor == "sqlite":
        connection.cursor().execute("PRAGMA journal_mode=WAL;")


connection_created.connect(_enable_sqlite_wal)

# No Redis for a single-church install: run Celery tasks synchronously.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]
