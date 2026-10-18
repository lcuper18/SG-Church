"""
E2E Tests: repeating events through the browser.
"""

import pytest

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.mark.e2e
@pytest.mark.django_db
class TestRecurrenceE2E:
    def test_create_a_weekly_series_cancel_one_and_edit_the_following(
        self, page, live_server_url, admin_user
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/events/create/")
        page.fill("#title", "Culto de miércoles")
        page.fill("#start_at", "2030-05-01T19:00")
        page.fill("#end_at", "2030-05-01T21:00")
        assert not page.is_visible("#repeat_weeks")
        page.check("#repeat")
        assert page.is_visible("#repeat_weeks")
        page.fill("#repeat_weeks", "4")
        page.click("button[type='submit']")

        content = page.content()
        assert "Se crearon 4 eventos" in content
        assert content.count("Culto de miércoles") >= 4

        # Cancel the second one only.
        page.goto(f"{live_server_url}/events/?page=1")
        page.click("a:has-text('Culto de miércoles') >> nth=1")
        page.click("a:has-text('Cancelar evento')")
        page.uncheck("#notify")
        page.click("button:has-text('Cancelar el evento')")
        assert "1 evento(s) cancelado(s)" in page.content()
        assert "Cancelado / inactivo" in page.content()

        # Rename this one and the following ones.
        page.click("a:has-text('Editar')")
        page.fill("#title", "Culto de oración")
        page.check("#edit_following")
        page.click("button:has-text('Guardar Cambios')")
        assert "También se actualizaron los 2 eventos siguientes" in page.content()

        page.goto(f"{live_server_url}/events/")
        content = page.content()
        assert content.count("Culto de oración") == 3 and content.count("Culto de miércoles") == 1
