"""
E2E Tests: a church with several sites (sedes).
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
class TestSitesE2E:
    def test_add_a_site_create_an_event_there_and_filter_by_it(self, page, live_server_url, admin_user):
        _login(page, live_server_url, admin_user)

        # With one site there is nothing to choose.
        page.goto(f"{live_server_url}/events/create/")
        assert page.locator("#site").count() == 0

        page.goto(f"{live_server_url}/sites/")
        page.click("a:has-text('Nueva sede')")
        page.fill("#id_name", "Sede Norte")
        page.fill("#id_address", "Avenida Norte 100")
        page.click("button:has-text('Guardar')")
        assert "Sede Norte" in page.content() and "Principal" in page.content()

        page.goto(f"{live_server_url}/events/create/")
        page.fill("#title", "Culto de miércoles")
        page.select_option("#site", label="Sede Norte")
        page.fill("#start_at", "2030-05-08T19:00")
        page.click("button[type='submit']")
        assert "Sede Norte" in page.content()

        page.goto(f"{live_server_url}/events/create/")
        page.fill("#title", "Culto central")
        page.fill("#start_at", "2030-05-09T19:00")
        page.click("button[type='submit']")

        page.goto(f"{live_server_url}/events/")
        page.select_option("select[name='site']", label="Sede Norte")
        page.click("button:has-text('Filtrar')")
        content = page.content()
        assert "Culto de miércoles" in content and "Culto central" not in content
