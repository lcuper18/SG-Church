"""
E2E Tests: taking attendance with visitors and reading the per-site summary.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Event
from members.models import Member
from tenants.models import Site

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.fixture
def culto_norte(admin_user):
    tenant = admin_user.tenant
    north = Site.objects.create(tenant=tenant, name="Sede Norte")
    Member.objects.create(tenant=tenant, first_name="Lucía", last_name="Presente")
    return Event.objects.create(
        tenant=tenant, title="Culto de miércoles", site=north, start_at=timezone.now() - timedelta(hours=2)
    )


@pytest.mark.e2e
@pytest.mark.django_db
class TestAttendanceBySiteE2E:
    def test_take_attendance_with_visitors_and_see_the_site_summary(
        self, page, live_server_url, admin_user, culto_norte
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/events/{culto_norte.pk}/attendance/")
        assert "Sede Norte" in page.content()
        page.check("input.attendance-box")
        page.fill("#guest_count", "6")
        page.click("button:has-text('Guardar asistencia')")
        assert "Asistencia guardada: 1 presentes" in page.content()

        page.goto(f"{live_server_url}/events/attendance/report/")
        assert page.inner_text("#kpi-guests") == "6"
        assert page.inner_text("#kpi-total") == "7"
        summary = page.inner_text("#site-summary")
        assert "Sede Norte" in summary and "7" in summary

        page.select_option("#site", label="Sede Norte")
        page.click("button:has-text('Ver reporte')")
        assert "Culto de miércoles" in page.content()
