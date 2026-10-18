"""
E2E Tests: sending a custom announcement from an event page.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

PASSWORD = "testpassword123"


@pytest.fixture
def event(admin_user):
    from events.models import Event, EventRegistration
    from members.models import Member

    tenant = admin_user.tenant
    event = Event.objects.create(tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=3))
    ana = Member.objects.create(tenant=tenant, first_name="Ana", last_name="Gómez", email="ana@iglesia.org")
    EventRegistration.objects.create(tenant=tenant, member=ana, event=event)
    return event


@pytest.mark.e2e
@pytest.mark.django_db
class TestEventAnnouncementsE2E:
    def test_send_now_then_schedule_and_cancel(self, event, page, live_server_url, admin_user):

        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/events/{event.pk}/")
        assert not page.is_visible("#ann_send_at")
        page.fill("#ann_subject", "Traer biblia")
        page.fill("#ann_body", "No olviden la biblia")
        page.click("#announce-form button[type='submit']")
        content = page.content()
        assert "Anuncio en camino a 1 destinatario" in content
        assert "Enviado" in content

        later = (timezone.localtime() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        page.fill("#ann_subject", "Recuerden el transporte")
        page.fill("#ann_body", "Salimos a las 7")
        page.select_option("#ann_when", "later")
        assert page.is_visible("#ann_send_at")
        page.fill("#ann_send_at", later)
        page.click("#announce-form button[type='submit']")
        assert "Anuncio programado para el" in page.content()

        page.click("button:has-text('Cancelar envío')")
        assert "Anuncio cancelado" in page.content()
