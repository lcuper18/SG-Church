"""
Recovering access without any mail server: the church administrator hands over a reset link,
and removes the two-step verification of someone who lost their phone.
"""

import re
import uuid

import pytest
from allauth.mfa import totp
from allauth.mfa.models import Authenticator
from django.core import mail
from django.test import Client
from django.urls import reverse

from core.models import AuditLog
from members.models import User

OLD = "Clave-Antigua-2026"
NEW = "Clave-Nueva-2027-xyz"


@pytest.fixture
def staff(admin_user):
    return User.objects.create_user(
        email=f"pastor-{uuid.uuid4().hex[:6]}@iglesia.org", password=OLD, role="pastor",
        tenant=admin_user.tenant, first_name="Pablo", last_name="Pastor",
    )


def link_from(response):
    return re.search(r'id="reset-url" value="([^"]+)"', response.content.decode()).group(1)


@pytest.mark.django_db
class TestResetLink:
    def test_the_admin_gets_a_link_that_really_sets_a_new_password(self, authenticated_client, staff):
        response = authenticated_client.post(reverse("user_reset_link", args=[staff.pk]))
        assert response.status_code == 200 and "3 días" in response.content.decode()
        url = link_from(response)
        assert "/accounts/password/reset/key/" in url

        person = Client()
        opened = person.get(url.split("://", 1)[1].split("/", 1)[1].join(["/", ""]), follow=True)
        assert opened.status_code == 200
        form_url = opened.redirect_chain[-1][0] if opened.redirect_chain else url
        done = person.post(form_url, {"password1": NEW, "password2": NEW}, follow=True)
        assert done.status_code == 200
        staff.refresh_from_db()
        assert staff.check_password(NEW) and not staff.check_password(OLD)

    def test_a_link_cannot_be_used_twice(self, authenticated_client, staff):
        url = link_from(authenticated_client.post(reverse("user_reset_link", args=[staff.pk])))
        path = "/" + url.split("://", 1)[1].split("/", 1)[1]
        first = Client()
        opened = first.get(path, follow=True)
        form_url = opened.redirect_chain[-1][0] if opened.redirect_chain else path
        first.post(form_url, {"password1": NEW, "password2": NEW}, follow=True)
        again = Client().get(path, follow=True)
        html = again.content.decode().lower()
        assert "password1" not in html  # no form to set a password: the link is spent
        staff.refresh_from_db()
        assert staff.check_password(NEW)

    def test_a_get_never_makes_a_link(self, authenticated_client, staff):
        assert authenticated_client.get(reverse("user_reset_link", args=[staff.pk])).status_code == 405

    def test_only_church_admins(self, regular_user_same_tenant, staff):
        plain = Client()
        plain.force_login(regular_user_same_tenant)
        assert plain.post(reverse("user_reset_link", args=[staff.pk])).status_code == 403

    def test_users_of_other_churches_are_off_limits(self, authenticated_client):
        from tenants.models import Tenant

        stranger = User.objects.create_user(
            email="x@otra.org", password=OLD, role="pastor", tenant=Tenant.objects.create(name="Otra", subdomain="otra-rl")
        )
        assert authenticated_client.post(reverse("user_reset_link", args=[stranger.pk])).status_code == 404

    def test_it_is_written_to_the_audit_log(self, authenticated_client, staff):
        authenticated_client.post(reverse("user_reset_link", args=[staff.pk]))
        assert AuditLog.objects.filter(object_repr__contains=f"restablecimiento de contraseña generado para {staff.email}").exists()

    def test_no_mail_is_involved(self, authenticated_client, staff):
        authenticated_client.post(reverse("user_reset_link", args=[staff.pk]))
        assert mail.outbox == []


@pytest.mark.django_db
class TestRemoveTwoStep:
    def enable(self, user):
        totp.TOTP.activate(user, totp.generate_totp_secret())

    def test_removes_it_and_the_person_can_sign_in_again(self, authenticated_client, staff):
        self.enable(staff)
        response = authenticated_client.post(reverse("user_remove_two_step", args=[staff.pk]), follow=True)
        assert "Se quitó la verificación" in response.content.decode()
        assert not Authenticator.objects.filter(user=staff).exists()
        login = Client().post(reverse("login"), {"login": staff.email, "password": OLD})
        assert login.status_code == 302 and "2fa" not in login.url

    def test_the_list_shows_the_button_only_for_those_who_have_it(self, authenticated_client, staff):
        assert "user_remove_two_step" not in authenticated_client.get(reverse("user_list")).content.decode() \
            and f"/users/{staff.pk}/remove-two-step/" not in authenticated_client.get(reverse("user_list")).content.decode()
        self.enable(staff)
        assert f"/users/{staff.pk}/remove-two-step/" in authenticated_client.get(reverse("user_list")).content.decode()

    def test_not_for_yourself(self, authenticated_client, admin_user):
        self.enable(admin_user)
        authenticated_client.post(reverse("user_remove_two_step", args=[admin_user.pk]))
        assert Authenticator.objects.filter(user=admin_user).exists()

    def test_only_church_admins_and_it_is_audited(self, admin_user, regular_user_same_tenant, staff):
        self.enable(staff)
        plain, boss = Client(), Client()  # separate sessions (the shared `client` fixture would mix them up)
        plain.force_login(regular_user_same_tenant)
        boss.force_login(admin_user)
        assert plain.post(reverse("user_remove_two_step", args=[staff.pk])).status_code == 403
        assert Authenticator.objects.filter(user=staff).exists()
        boss.post(reverse("user_remove_two_step", args=[staff.pk]))
        assert AuditLog.objects.filter(object_repr__contains="Verificación en dos pasos quitada").exists()
