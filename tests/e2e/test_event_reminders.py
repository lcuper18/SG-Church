"""
E2E Tests: turning the automatic reminders of an event on and off.
"""

import pytest

PASSWORD = "testpassword123"


@pytest.mark.e2e
@pytest.mark.django_db
class TestEventRemindersE2E:
    def test_reminders_can_be_switched_off_for_an_event(self, page, live_server_url, admin_user):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/events/create/")
        assert page.is_checked("#reminders_enabled")
        page.fill("#title", "Vigilia")
        page.fill("#start_at", "2030-05-01T19:00")
        page.uncheck("#reminders_enabled")
        page.click("button[type='submit']")
        assert "Desactivados" in page.content()

        page.click("a:has-text('Editar')")
        assert not page.is_checked("#reminders_enabled")
        page.check("#reminders_enabled")
        page.click("button[type='submit']")
        assert "Automáticos: 1 día y 1 hora antes" in page.content()
