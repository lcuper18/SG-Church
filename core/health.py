"""
Health endpoint for the load balancer and external uptime monitors.

200 means the app can serve requests. The database is essential (503 if it
is down); Redis is not -- mail falls back to sending inline and the site keeps
working -- so a Redis outage reports "degraded" with 200 and is visible in the
JSON for whoever watches it.
"""

import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return "ok"
    except Exception:  # noqa: BLE001
        logger.exception("Health check: database unreachable")
        return "error"


def _check_broker():
    """Redis behind Celery; not applicable when tasks run eagerly (tests and
    single-church installs)."""
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return "not used"
    url = getattr(settings, "CELERY_BROKER_URL", "")
    if not url.startswith("redis"):
        return "not used"
    try:
        import redis

        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return "ok"
    except Exception:  # noqa: BLE001
        logger.warning("Health check: broker unreachable", exc_info=True)
        return "error"


def health_check(request):
    database, broker = _check_database(), _check_broker()
    if database != "ok":
        status, code = "down", 503
    elif broker == "error":
        status, code = "degraded", 200
    else:
        status, code = "ok", 200
    return JsonResponse({"status": status, "database": database, "broker": broker}, status=code)
