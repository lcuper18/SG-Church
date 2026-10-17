"""
/health/ reports the database (essential) and Redis (degrades, doesn't fail).
"""

from unittest import mock

import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealth:
    def test_ok_without_logging_in(self):
        response = Client().get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok", "broker": "not used"}

    def test_database_down_is_a_503(self):
        broken = mock.MagicMock()
        broken.cursor.side_effect = RuntimeError("connection refused")
        with mock.patch("core.health.connection", broken):
            response = Client().get("/health/")

        assert response.status_code == 503
        assert response.json()["status"] == "down"
        assert response.json()["database"] == "error"

    def test_redis_down_is_degraded_but_still_200(self, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = False
        settings.CELERY_BROKER_URL = "redis://127.0.0.1:1/0"

        response = Client().get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "degraded", "database": "ok", "broker": "error"}

    def test_redis_up_is_ok(self, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = False
        settings.CELERY_BROKER_URL = "redis://redis.example:6379/0"
        with mock.patch("redis.Redis.from_url") as from_url:
            from_url.return_value.ping.return_value = True
            response = Client().get("/health/")

        assert response.json()["broker"] == "ok" and response.json()["status"] == "ok"
