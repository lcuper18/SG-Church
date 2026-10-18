"""
E2E Tests: signing in with two-step verification, and the lock after too many wrong passwords.
"""

import pytest

PASSWORD = "testpassword123"


@pytest.fixture
def protected(admin_user):
    from allauth.mfa import totp

    secret = totp.generate_totp_secret()
    totp.TOTP.activate(admin_user, secret)
    return secret


def current_code(secret):
    from allauth.mfa import totp

    return totp.format_hotp_value(totp.hotp_value(secret, totp.hotp_counter_from_time()))


@pytest.mark.e2e
@pytest.mark.django_db
class TestTwoStepE2E:
    def test_login_asks_for_the_code(self, protected, page, live_server_url, admin_user):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_url("**/accounts/2fa/authenticate/")
        assert "Verificación en dos pasos" in page.content()

        page.fill("#id_code", "000000")
        page.click("button[type='submit']")
        assert "/2fa/authenticate/" in page.url  # still asked

        page.fill("#id_code", current_code(protected))
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/" not in url)

    def test_repeated_wrong_passwords_lock_the_login(self, page, live_server_url, admin_user):
        for _ in range(5):
            page.goto(f"{live_server_url}/accounts/login/")
            page.fill("#id_login", admin_user.email)
            page.fill("#id_password", "incorrecta")
            page.click("button[type='submit']")
            page.wait_for_selector(".alert-danger")
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", PASSWORD)  # even the right one is refused now
        page.click("button[type='submit']")
        page.wait_for_selector(".alert-danger")
        assert "/accounts/login/" in page.url
