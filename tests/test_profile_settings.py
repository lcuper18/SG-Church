"""Profile page (any user) and church settings page (administrators only)."""

import pytest
from django.urls import reverse

from finance.models import Donation
from members.models import User


@pytest.mark.django_db
class TestProfile:
    def test_requires_login(self, client):
        response = client.get(reverse("profile"))
        assert response.status_code == 302 and "login" in response.url

    def test_updates_name_but_not_email(self, authenticated_client, admin_user):
        original_email = admin_user.email
        response = authenticated_client.post(
            reverse("profile"),
            {"action": "profile", "first_name": "Ana", "last_name": "Mora", "email": "otro@x.com"},
        )
        assert response.status_code == 302
        admin_user.refresh_from_db()
        assert (admin_user.first_name, admin_user.last_name) == ("Ana", "Mora")
        assert admin_user.email == original_email

    def test_changes_password_and_keeps_session(self, authenticated_client, admin_user):
        response = authenticated_client.post(
            reverse("profile"),
            {
                "action": "password",
                "old_password": "testpassword123",
                "new_password1": "una-clave-nueva-9876",
                "new_password2": "una-clave-nueva-9876",
            },
        )
        assert response.status_code == 302
        admin_user.refresh_from_db()
        assert admin_user.check_password("una-clave-nueva-9876")
        assert authenticated_client.get(reverse("profile")).status_code == 200

    def test_wrong_current_password_shows_error(self, authenticated_client, admin_user):
        response = authenticated_client.post(
            reverse("profile"),
            {
                "action": "password",
                "old_password": "incorrecta",
                "new_password1": "una-clave-nueva-9876",
                "new_password2": "una-clave-nueva-9876",
            },
        )
        assert response.status_code == 200
        assert "is-invalid" in response.content.decode()
        admin_user.refresh_from_db()
        assert admin_user.check_password("testpassword123")


@pytest.mark.django_db
class TestChurchSettings:
    def _data(self, tenant, **overrides):
        data = {
            "name": tenant.name,
            "denomination": "",
            "country": "CR",
            "city": "San José",
            "state": "",
            "address": "",
            "phone": "",
            "email": "",
            "currency": tenant.currency,
            "timezone": tenant.timezone,
            "enable_families": "on",
            "enable_tags": "on",
        }
        data.update(overrides)
        return data

    def test_admin_updates_settings(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        response = authenticated_client.post(
            reverse("church_settings"),
            self._data(tenant, name="Iglesia Nueva", currency="CRC", timezone="America/Costa_Rica"),
        )
        assert response.status_code == 302
        tenant.refresh_from_db()
        assert (tenant.name, tenant.currency, tenant.timezone) == (
            "Iglesia Nueva", "CRC", "America/Costa_Rica",
        )

    def test_unchecking_modules_disables_them(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        data = self._data(tenant)
        del data["enable_tags"]
        authenticated_client.post(reverse("church_settings"), data)
        tenant.refresh_from_db()
        assert tenant.enable_families and not tenant.enable_tags
        page = authenticated_client.get(reverse("profile")).content.decode()
        assert "Etiquetas" not in page and "Familias" in page

    def test_unknown_timezone_is_rejected(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        response = authenticated_client.post(
            reverse("church_settings"), self._data(tenant, timezone="Mars/Olympus_Mons")
        )
        assert response.status_code == 200
        tenant.refresh_from_db()
        assert tenant.timezone != "Mars/Olympus_Mons"

    def test_legacy_timezone_stays_selectable(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        tenant.timezone = "America/Buenos_Aires"  # from the old onboarding list
        tenant.save()
        page = authenticated_client.get(reverse("church_settings")).content.decode()
        assert '<option value="America/Buenos_Aires" selected>' in page

    def test_warns_about_currency_only_when_there_is_financial_data(
        self, authenticated_client, admin_user
    ):
        url = reverse("church_settings")
        assert "no convierte importes" not in authenticated_client.get(url).content.decode()
        Donation.objects.create(tenant=admin_user.tenant, amount=10)
        assert "no convierte importes" in authenticated_client.get(url).content.decode()

    def test_non_admin_gets_403_and_no_menu_entry(self, client, admin_user):
        user = User.objects.create_user(
            email="member@x.com", password="testpassword123", tenant=admin_user.tenant, role="member"
        )
        client.force_login(user)
        assert client.get(reverse("church_settings")).status_code == 403
        assert reverse("church_settings") not in client.get(reverse("profile")).content.decode()

    def test_admin_sees_menu_entry(self, authenticated_client):
        page = authenticated_client.get(reverse("profile")).content.decode()
        assert reverse("church_settings") in page

    def test_anonymous_is_redirected_to_login(self, client):
        response = client.get(reverse("church_settings"))
        assert response.status_code == 302 and "login" in response.url
