"""
E2E Tests: user management (administrators only).
"""

import pytest


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", "testpassword123")
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.mark.e2e
@pytest.mark.django_db
class TestUsersE2E:
    def test_admin_creates_a_user_from_the_menu_and_sees_them_listed(
        self, page, live_server_url, admin_user
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/users/")
        page.click("a:has-text('Nuevo usuario')")
        page.fill("#id_first_name", "Suhellen")
        page.fill("#id_last_name", "Fallas")
        page.fill("#id_email", "suhellen@e2e.test")
        page.select_option("#id_role", "treasurer")
        page.fill("#id_password1", "Clave-Segura-2026")
        page.fill("#id_password2", "Clave-Segura-2026")
        page.click("button:has-text('Crear usuario')")

        assert page.url.rstrip("/").endswith("/users")
        assert "Suhellen Fallas" in page.content()
        assert "suhellen@e2e.test" in page.content()
        assert "Tesorero" in page.content()

    def test_mismatched_passwords_show_an_error(self, page, live_server_url, admin_user):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/users/create/")
        page.fill("#id_first_name", "Ana")
        page.fill("#id_email", "ana@e2e.test")
        page.fill("#id_password1", "Clave-Segura-2026")
        page.fill("#id_password2", "otra-distinta-77")
        page.click("button:has-text('Crear usuario')")

        assert "Las contraseñas no coinciden" in page.content()
