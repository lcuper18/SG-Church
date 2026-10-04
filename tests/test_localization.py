"""
Per-church currency and time zone: the {% money %} tag formats with the
church's currency, TenantMiddleware activates its time zone, and onboarding /
create_tenant accept and validate both.
"""

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone, translation

from events.models import Event
from tenants.middleware import TenantMiddleware
from tenants.models import Tenant


def _money(expr, **context):
    with translation.override("es"):
        return Template("{% load ui %}" + expr).render(Context(context))


class TestMoneyTag:
    def test_uses_symbol_and_locale_separators(self):
        # El locale "es" agrupa los miles con un espacio de no separación.
        assert _money("{% money 2068 'USD' %}") == "$2\xa0068,00"
        assert _money("{% money amount 'CRC' %}", amount=Decimal("1234.5")) == "₡1\xa0234,50"

    def test_currency_without_cents_has_no_decimals(self):
        assert _money("{% money 1500 'CLP' %}") == "CL$1\xa0500"

    def test_negative_amount_puts_sign_before_symbol(self):
        assert _money("{% money -1392 'USD' %}") == "-$1\xa0392,00"

    def test_amount_that_rounds_to_zero_has_no_sign(self):
        assert _money("{% money -0.001 'USD' %}") == "$0,00"

    def test_missing_amount_shows_dash(self):
        assert _money("{% money amount 'USD' %}", amount=None) == "-"

    def test_defaults_to_tenant_currency_from_context(self):
        tenant = Tenant(name="Iglesia", subdomain="x", currency="CRC")
        assert _money("{% money 10 %}", tenant=tenant) == "₡10,00"

    def test_falls_back_to_usd_without_tenant(self):
        assert _money("{% money 10 %}") == "$10,00"

    def test_unknown_currency_uses_its_code_as_symbol(self):
        assert _money("{% money 10 'XYZ' %}") == "XYZ10,00"

    def test_currency_symbol_tag(self):
        assert _money("{% currency_symbol 'CRC' %}") == "₡"


@pytest.mark.django_db
class TestMiddlewareTimezone:
    def _active_zone(self, user):
        seen = {}

        def get_response(request):
            seen["zone"] = timezone.get_current_timezone_name()
            return None

        request = RequestFactory().get("/dashboard/")
        request.user = user
        TenantMiddleware(get_response)(request)
        return seen["zone"]

    def test_activates_the_users_church_timezone(self, admin_user):
        admin_user.tenant.timezone = "America/Costa_Rica"
        admin_user.tenant.save()
        assert self._active_zone(admin_user) == "America/Costa_Rica"

    def test_deactivates_after_the_request(self, admin_user):
        admin_user.tenant.timezone = "America/Costa_Rica"
        admin_user.tenant.save()
        self._active_zone(admin_user)
        assert timezone.get_current_timezone_name() != "America/Costa_Rica"

    def test_unknown_timezone_keeps_the_default(self, admin_user):
        admin_user.tenant.timezone = "Mars/Olympus_Mons"
        admin_user.tenant.save()
        assert self._active_zone(admin_user) == timezone.get_default_timezone_name()


@pytest.mark.django_db
class TestLocalizedPages:
    def test_event_time_is_shown_in_the_churchs_timezone(self, authenticated_client, admin_user):
        admin_user.tenant.timezone = "America/Costa_Rica"
        admin_user.tenant.save()
        # 01:00 UTC on the 16th is 19:00 on the 15th in Costa Rica (UTC-6).
        Event.objects.create(
            tenant=admin_user.tenant,
            title="Culto de jóvenes",
            start_at=datetime(2026, 1, 16, 1, 0, tzinfo=dt_timezone.utc),
        )
        page = authenticated_client.get("/events/").content.decode()
        assert "15/01/2026 19:00" in page

    def test_finance_dashboard_uses_the_tenant_currency(self, authenticated_client, admin_user):
        admin_user.tenant.currency = "CRC"
        admin_user.tenant.save()
        page = authenticated_client.get("/finance/").content.decode()
        assert "₡0,00" in page
        assert "$0,00" not in page


@pytest.mark.django_db
class TestOnboardingSettings:
    def _prepare(self, client, country):
        session = client.session
        session["onboarding_church"] = {"name": "Iglesia", "country": country}
        session["onboarding_admin"] = {"email": "a@b.com"}
        session.save()

    def test_preselects_timezone_and_currency_for_the_country(self, client):
        self._prepare(client, "CR")
        page = client.get(reverse("onboarding_settings")).content.decode()
        assert '<option value="America/Costa_Rica" selected>' in page
        assert '<option value="CRC" selected>' in page

    def test_unknown_country_falls_back_to_defaults(self, client):
        self._prepare(client, "")
        page = client.get(reverse("onboarding_settings")).content.decode()
        assert '<option value="America/New_York" selected>' in page
        assert '<option value="USD" selected>' in page

    def test_invalid_posted_timezone_is_replaced_by_the_default(self, client):
        self._prepare(client, "CR")
        client.post(
            reverse("onboarding_settings"),
            {"currency": "CRC", "timezone": "Not/AZone"},
        )
        assert client.session["onboarding_settings"]["timezone"] == "America/New_York"


@pytest.mark.django_db
class TestCreateTenantCommand:
    def test_stores_currency_and_timezone(self):
        call_command(
            "create_tenant", "Iglesia Central", "central",
            currency="crc", timezone="America/Costa_Rica",
        )
        tenant = Tenant.objects.get(subdomain="central")
        assert (tenant.currency, tenant.timezone) == ("CRC", "America/Costa_Rica")

    def test_rejects_unknown_currency(self):
        with pytest.raises(CommandError):
            call_command("create_tenant", "X", "x", currency="ZZZ")
        assert not Tenant.objects.filter(subdomain="x").exists()

    def test_rejects_unknown_timezone(self):
        with pytest.raises(CommandError):
            call_command("create_tenant", "X", "x", timezone="Mars/Olympus_Mons")
        assert not Tenant.objects.filter(subdomain="x").exists()
