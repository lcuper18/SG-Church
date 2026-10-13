"""
CSV exports (members, donations, expenses, attendance) and the income
statement's month boundaries.
"""

import csv
import io
import uuid
import warnings
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.exports import cell
from events.models import Event, EventAttendance, EventRegistration
from finance.models import Donation, Expense
from members.models import Family, Member, Tag, User
from tenants.models import Tenant

PASSWORD = "testpassword123"


def _rows(response):
    text = response.content.decode("utf-8")
    assert text.startswith("﻿"), "Excel needs the BOM to read accents"
    return list(csv.reader(io.StringIO(text.lstrip("﻿"))))


def _client_for(tenant, role):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=PASSWORD, role=role, tenant=tenant
    )
    client = Client()
    client.force_login(user)
    return client


def _member(tenant, first, last="Demo", **kwargs):
    return Member.objects.create(tenant=tenant, first_name=first, last_name=last, **kwargs)


def _donation(tenant, when, amount="100.00", **kwargs):
    donation = Donation.objects.create(
        tenant=tenant, amount=Decimal(amount), status="completed", **kwargs
    )
    Donation.objects.filter(pk=donation.pk).update(donation_date=when)  # auto_now_add
    return donation


class TestCell:
    @pytest.mark.parametrize("text", ["=1+1", "+cmd", "-2+3", "@SUM(A1)", "\tx"])
    def test_formula_like_text_is_neutralised(self, text):
        assert cell(text) == f"'{text}"

    def test_normal_values_pass_through(self):
        assert cell("María") == "María"
        assert cell(None) == ""
        assert cell(True) == "Sí" and cell(False) == "No"
        assert cell(Decimal("12.5")) == "12.50"
        assert cell(-5) == -5  # numbers are never treated as formulas

    def test_datetimes_are_shown_in_the_active_time_zone(self):
        utc = datetime(2026, 11, 1, 3, 30, tzinfo=dt_timezone.utc)
        with timezone.override("America/Costa_Rica"):
            assert cell(utc) == "2026-10-31 21:30"


@pytest.mark.django_db
class TestMemberExport:
    def test_requires_a_role_that_manages_members(self, admin_user):
        url = reverse("member_export")
        assert Client().get(url).status_code == 302
        for role in ("member", "teacher", "treasurer"):
            assert _client_for(admin_user.tenant, role).get(url).status_code == 403
        for role in ("admin", "pastor", "volunteer"):
            assert _client_for(admin_user.tenant, role).get(url).status_code == 200

    def test_exports_this_churchs_members_with_readable_labels(
        self, authenticated_client, admin_user
    ):
        tenant = admin_user.tenant
        family = Family.objects.create(tenant=tenant, name="Familia Mora")
        tag = Tag.objects.create(tenant=tenant, name="Música")
        ana = _member(
            tenant, "Ana", "Mora", gender="female", marital_status="married",
            is_baptized=True, member_status="member", family=family, email="ana@x.com",
        )
        ana.tags.add(tag)
        _member(Tenant.objects.create(name="Otra", subdomain="otra-exp"), "Ajeno")

        response = authenticated_client.get(reverse("member_export"))
        rows = _rows(response)

        assert response["Content-Type"].startswith("text/csv")
        assert response["Content-Disposition"].startswith('attachment; filename="miembros-')
        header, body = rows[0], rows[1:]
        assert len(body) == 1
        record = dict(zip(header, body[0]))
        assert record["Nombre"] == "Ana" and record["Email"] == "ana@x.com"
        assert record["Género"] == "Femenino" and record["Estado civil"] == "Casado/a"
        assert record["Bautizado"] == "Sí" and record["Estado"] == "Miembro"
        assert record["Familia"] == "Familia Mora" and record["Etiquetas"] == "Música"

    def test_applies_the_lists_filters(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        _member(tenant, "Ana", member_status="member")
        _member(tenant, "Beto", member_status="visitor")

        by_status = _rows(authenticated_client.get(reverse("member_export"), {"status": "visitor"}))
        by_search = _rows(authenticated_client.get(reverse("member_export"), {"search": "ana"}))

        assert [r[0] for r in by_status[1:]] == ["Beto"]
        assert [r[0] for r in by_search[1:]] == ["Ana"]

    def test_user_entered_formulas_do_not_reach_excel_as_formulas(
        self, authenticated_client, admin_user
    ):
        _member(admin_user.tenant, '=HYPERLINK("http://evil","x")', "+cmd")

        row = _rows(authenticated_client.get(reverse("member_export")))[1]

        assert row[0].startswith("'=") and row[1].startswith("'+")

    def test_button_shows_for_managers_and_keeps_the_filters(
        self, authenticated_client, admin_user
    ):
        html = authenticated_client.get(reverse("member_list"), {"status": "visitor"}).content.decode()
        assert f'{reverse("member_export")}?status=visitor' in html

    def test_button_hidden_for_read_only_roles(self, admin_user):
        html = _client_for(admin_user.tenant, "member").get(reverse("member_list")).content.decode()
        assert reverse("member_export") not in html


@pytest.mark.django_db
class TestFinanceExports:
    @pytest.fixture(autouse=True)
    def _costa_rica(self, admin_user):
        admin_user.tenant.timezone = "America/Costa_Rica"
        admin_user.tenant.currency = "CRC"
        admin_user.tenant.save()

    def test_only_finance_roles_can_export(self, admin_user):
        for name in ("donation_export", "expense_export"):
            url = reverse(name)
            for role in ("pastor", "teacher", "volunteer", "member"):
                assert _client_for(admin_user.tenant, role).get(url).status_code == 403
            for role in ("admin", "treasurer"):
                assert _client_for(admin_user.tenant, role).get(url).status_code == 200

    def test_donations_use_local_dates_and_include_the_last_day(
        self, authenticated_client, admin_user
    ):
        tenant = admin_user.tenant
        # 03:30 UTC on Nov 1st is 21:30 on Oct 31st in Costa Rica.
        late = _donation(tenant, datetime(2026, 11, 1, 3, 30, tzinfo=dt_timezone.utc), "250.00",
                         donor_name="Don Pedro", currency="CRC", campaign="tithe")
        _donation(tenant, datetime(2026, 11, 1, 18, 0, tzinfo=dt_timezone.utc), "999.00")

        rows = _rows(authenticated_client.get(
            reverse("donation_export"), {"date_from": "2026-10-01", "date_to": "2026-10-31"}
        ))

        assert len(rows) == 2  # header + the Oct 31st one, not the Nov 1st one
        record = dict(zip(rows[0], rows[1]))
        assert record["Fecha"] == "2026-10-31 21:30"
        assert record["Donante"] == "Don Pedro" and record["Monto"] == "250.00"
        assert record["Moneda"] == "CRC" and record["Campaña"] == "Diezmo"
        assert late.pk  # created

    def test_anonymous_and_member_donors(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        ana = _member(tenant, "Ana", "Mora", email="ana@x.com")
        now = timezone.now()
        _donation(tenant, now, member=ana)
        _donation(tenant, now, anonymous=True, donor_name="Secreto")

        names = {r[1] for r in _rows(authenticated_client.get(reverse("donation_export")))[1:]}

        assert names == {"Ana Mora", "Anónimo"}  # the anonymous donor's name is not leaked

    def test_donation_list_includes_the_end_date_too(self, authenticated_client, admin_user):
        _donation(admin_user.tenant, datetime(2026, 11, 1, 3, 30, tzinfo=dt_timezone.utc), "10.00")

        response = authenticated_client.get(
            reverse("donation_list"), {"date_from": "2026-10-31", "date_to": "2026-10-31"}
        )

        assert len(response.context["donations"]) == 1

    def test_expenses_export_respects_filters(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        Expense.objects.create(tenant=tenant, description="Luz", amount=Decimal("45"),
                               expense_date=datetime(2026, 10, 5).date(), category="utilities")
        Expense.objects.create(tenant=tenant, description="Sonido", amount=Decimal("90"),
                               expense_date=datetime(2026, 9, 5).date(), category="maintenance")

        rows = _rows(authenticated_client.get(reverse("expense_export"), {"date_from": "2026-10-01"}))

        assert [r[1] for r in rows[1:]] == ["Luz"]
        assert dict(zip(rows[0], rows[1]))["Categoría"] == "Servicios"


@pytest.mark.django_db
class TestAttendanceExport:
    @pytest.fixture
    def attended(self, admin_user):
        tenant = admin_user.tenant
        ana, beto = _member(tenant, "Ana"), _member(tenant, "Beto")
        event = Event.objects.create(
            tenant=tenant, title="Culto", event_type="service",
            start_at=timezone.now() - timedelta(days=3),
        )
        EventRegistration.objects.create(tenant=tenant, member=ana, event=event)
        EventRegistration.objects.create(tenant=tenant, member=beto, event=event)
        EventAttendance.objects.create(tenant=tenant, member=ana, event=event)
        return event

    def test_requires_a_member_managing_role(self, admin_user):
        url = reverse("attendance_export")
        assert _client_for(admin_user.tenant, "member").get(url).status_code == 403
        assert _client_for(admin_user.tenant, "pastor").get(url).status_code == 200

    def test_per_event(self, authenticated_client, attended):
        rows = _rows(authenticated_client.get(reverse("attendance_export")))

        record = dict(zip(rows[0], rows[1]))
        assert record["Evento"] == "Culto" and record["Tipo"] == "Servicio"
        assert (record["Inscritos"], record["Asistieron"]) == ("2", "1")

    def test_per_member(self, authenticated_client, attended):
        rows = _rows(authenticated_client.get(reverse("attendance_export"), {"kind": "members"}))

        assert [r[0] for r in rows[1:]] == ["Ana"]  # Beto registered but never came
        assert dict(zip(rows[0], rows[1]))["% de eventos"] == "100"

    def test_range_and_type_filters(self, authenticated_client, attended):
        outside = authenticated_client.get(
            reverse("attendance_export"), {"start": "2020-01-01", "end": "2020-12-31"}
        )
        other_type = authenticated_client.get(reverse("attendance_export"), {"type": "camp"})

        assert len(_rows(outside)) == 1 and len(_rows(other_type)) == 1


@pytest.mark.django_db
class TestIncomeStatementBoundaries:
    @pytest.fixture(autouse=True)
    def _costa_rica(self, admin_user):
        admin_user.tenant.timezone = "America/Costa_Rica"
        admin_user.tenant.save()

    def test_month_follows_the_churchs_calendar_not_utc(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        # Oct 31 21:30 local (counts for October) vs Nov 1 00:30 local (November).
        _donation(tenant, datetime(2026, 11, 1, 3, 30, tzinfo=dt_timezone.utc), "100.00")
        _donation(tenant, datetime(2026, 11, 1, 6, 30, tzinfo=dt_timezone.utc), "7.00")

        october = authenticated_client.get(reverse("income_statement"), {"month": 10, "year": 2026})
        november = authenticated_client.get(reverse("income_statement"), {"month": 11, "year": 2026})

        assert october.context["total_donations"] == Decimal("100.00")
        assert november.context["total_donations"] == Decimal("7.00")

    def test_builds_no_naive_datetimes(self, authenticated_client, admin_user):
        _donation(admin_user.tenant, timezone.now(), "5.00")
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            response = authenticated_client.get(reverse("income_statement"), {"month": 3, "year": 2026})
        assert response.status_code == 200

    @pytest.mark.parametrize("params", [{"month": "abc"}, {"month": 13}, {"year": 1}, {"year": "x", "month": 0}])
    def test_junk_parameters_do_not_crash(self, authenticated_client, params):
        assert authenticated_client.get(reverse("income_statement"), params).status_code == 200
