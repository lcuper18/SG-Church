"""
Login security: attempt limits (per e-mail and per address, with a trustworthy client
address behind a proxy), password-reset throttling, and two-step verification.
"""

import uuid

import pytest
from allauth.mfa import totp
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes import RecoveryCodes
from django.core import mail
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.urls import reverse

from core.adapters import AccountAdapter
from members.models import User

PASSWORD = "Clave-Segura-2026"


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def person(admin_user):
    return User.objects.create_user(
        email=f"p-{uuid.uuid4().hex[:6]}@iglesia.org", password=PASSWORD, role="pastor", tenant=admin_user.tenant
    )


def try_login(client, email, password, **extra):
    return client.post(reverse("login"), {"login": email, "password": password}, **extra)


@pytest.mark.django_db
class TestAttemptLimits:
    def test_five_wrong_passwords_lock_the_account_even_for_the_right_one(self, person):
        client = Client()
        for _ in range(5):
            assert try_login(client, person.email, "mala").status_code == 200
        response = try_login(client, person.email, PASSWORD)
        assert response.status_code == 200 and "_auth_user_id" not in client.session
        assert "Demasiados" in response.content.decode() or "intentos" in response.content.decode()

    def test_another_account_is_not_affected(self, person, admin_user):
        client = Client()
        for _ in range(6):
            try_login(client, person.email, "mala")
        other = Client()
        assert try_login(other, admin_user.email, "testpassword123").status_code == 302

    def test_changing_the_address_does_not_reset_the_per_account_limit(self, person):
        for number in range(5):
            try_login(Client(), person.email, "mala", REMOTE_ADDR=f"10.0.0.{number}")
        response = try_login(Client(), person.email, PASSWORD, REMOTE_ADDR="10.0.0.99")
        assert response.status_code == 200

    def test_the_per_address_limit_counts_many_accounts(self):
        client = Client()
        for number in range(10):
            try_login(client, f"nadie{number}@x.org", "mala")
        # the 11th attempt from the same address is refused before checking anything
        response = try_login(client, "otro@x.org", "mala")
        assert response.status_code == 200
        assert "Demasiados" in response.content.decode() or "intentos" in response.content.decode()


@pytest.mark.django_db
class TestClientAddress:
    def adapter_ip(self, settings, hops, forwarded, remote="172.18.0.5"):
        settings.TRUSTED_PROXY_COUNT = hops
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR=remote)
        return AccountAdapter().get_client_ip(request)

    def test_a_forged_header_cannot_choose_the_address(self, settings):
        # The client sent "1.1.1.1"; our proxy appended the real address after it.
        assert self.adapter_ip(settings, 1, "1.1.1.1, 203.0.113.9") == "203.0.113.9"

    def test_without_proxies_the_header_is_ignored(self, settings):
        assert self.adapter_ip(settings, 0, "1.1.1.1") == "172.18.0.5"

    def test_a_missing_header_falls_back_to_the_connection(self, settings):
        assert self.adapter_ip(settings, 1, "") == "172.18.0.5"


@pytest.mark.django_db
class TestPasswordResetThrottle:
    def test_repeated_requests_for_one_address_stop_sending_mail(self, person):
        client = Client()
        statuses = [client.post(reverse("password_reset"), {"email": person.email}).status_code for _ in range(6)]
        assert len(mail.outbox) <= 3
        assert statuses[-1] == 429  # a proper "too many attempts" page, not a server error
        assert "Demasiados intentos" in client.post(reverse("password_reset"), {"email": person.email}).content.decode()


def enable_totp(user):
    secret = totp.generate_totp_secret()
    totp.TOTP.activate(user, secret)
    return secret


def just_logged_in(client, at=None):
    """force_login skips allauth, which records when the password was typed."""
    import time

    session = client.session
    session["account_authentication_methods"] = [{"method": "password", "at": at or time.time()}]
    session.save()


def current_code(secret):
    return totp.format_hotp_value(totp.hotp_value(secret, totp.hotp_counter_from_time()))


@pytest.mark.django_db
class TestTwoStep:
    def test_without_it_login_is_unchanged(self, person):
        response = try_login(Client(), person.email, PASSWORD)
        assert response.status_code == 302 and "2fa" not in response.url

    def test_with_it_a_code_is_asked_after_the_password(self, person):
        secret = enable_totp(person)
        client = Client()
        response = try_login(client, person.email, PASSWORD)
        assert response.status_code == 302 and response.url.endswith("/accounts/2fa/authenticate/")
        assert "_auth_user_id" not in client.session  # not logged in yet
        assert "Verificación en dos pasos" in client.get(response.url).content.decode()

        wrong = client.post(response.url, {"code": "000000"})
        assert wrong.status_code == 200 and "_auth_user_id" not in client.session

        good = client.post(response.url, {"code": current_code(secret)})
        assert good.status_code == 302 and "_auth_user_id" in client.session

    def test_a_recovery_code_works_once(self, person):
        enable_totp(person)
        code = RecoveryCodes.activate(person).get_unused_codes()[0]
        client = Client()
        url = try_login(client, person.email, PASSWORD).url
        assert client.post(url, {"code": code}).status_code == 302
        second = Client()
        url = try_login(second, person.email, PASSWORD).url
        assert second.post(url, {"code": code}).status_code == 200  # already used

    def test_guessing_codes_is_limited(self, person):
        secret = enable_totp(person)
        client = Client()
        url = try_login(client, person.email, PASSWORD).url
        for _ in range(12):
            client.post(url, {"code": "000000"})
        client.post(url, {"code": current_code(secret)})
        assert "_auth_user_id" not in client.session  # even the right code is refused now

    def test_setting_it_up_from_the_security_page(self, person):
        client = Client()
        client.force_login(person)
        just_logged_in(client)
        page = client.get(reverse("mfa_index")).content.decode()
        assert "Activar la verificación en dos pasos" in page
        activate = client.get(reverse("mfa_activate_totp"))
        assert activate.status_code == 200 and "data:image/svg+xml" in activate.content.decode()
        secret = client.session["mfa.totp.secret"]
        done = client.post(reverse("mfa_activate_totp"), {"code": current_code(secret)})
        assert done.status_code == 302
        assert Authenticator.objects.filter(user=person, type="totp").exists()
        assert Authenticator.objects.filter(user=person, type="recovery_codes").exists()

    def test_turning_it_off_needs_a_recent_login(self, person):
        enable_totp(person)
        client = Client()
        client.force_login(person)
        just_logged_in(client, at=1)  # long ago
        response = client.get(reverse("mfa_deactivate_totp"))
        assert response.status_code == 302 and "reauthenticate" in response.url


@pytest.mark.django_db
class TestNudgeAndMenu:
    def test_admins_without_it_see_the_suggestion(self, authenticated_client, admin_user):
        admin_user.tenant.onboarding_completed = True
        admin_user.tenant.save()
        html = authenticated_client.get(reverse("dashboard")).content.decode()
        assert "two-step-nudge" in html and "Seguridad (2 pasos)" in html

    def test_it_goes_away_once_enabled(self, authenticated_client, admin_user):
        admin_user.tenant.onboarding_completed = True
        admin_user.tenant.save()
        enable_totp(admin_user)
        assert "two-step-nudge" not in authenticated_client.get(reverse("dashboard")).content.decode()
