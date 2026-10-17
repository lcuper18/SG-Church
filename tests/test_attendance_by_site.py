"""
Attendance per site: visitors (a head-count of non-members) per event, the
report's site filter and "resumen por sede", and the CSV exports.
"""

import csv
import io
import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from events.models import Event, EventAttendance, EventRegistration
from members.models import Member, User
from tenants.models import Site


def rows_of(response):
    text = response.content.decode("utf-8").lstrip("﻿")
    return list(csv.reader(io.StringIO(text)))


def person(tenant, name, home_site=None):
    return Member.objects.create(tenant=tenant, first_name=name, last_name="Prueba", home_site=home_site)


def held(tenant, title, site=None, days_ago=1, guests=0, present=(), registered=()):
    event = Event.objects.create(
        tenant=tenant, title=title, site=site, guest_count=guests,
        start_at=timezone.now() - timedelta(days=days_ago),
    )
    for member in present:
        EventAttendance.objects.create(tenant=tenant, member=member, event=event)
    for member in registered:
        EventRegistration.objects.create(tenant=tenant, member=member, event=event)
    return event


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def sites(tenant):
    return tenant.main_site(), Site.objects.create(tenant=tenant, name="Sede Norte")


@pytest.fixture
def scenario(tenant, sites):
    """Central: 2 events (3 and 1 members, 2+4 visitors). Norte: 1 event (2 members, 5 visitors),
    one of whose members belongs to Central."""
    central, north = sites
    c1, c2, n1 = person(tenant, "C1", central), person(tenant, "C2", central), person(tenant, "N1", north)
    n2 = person(tenant, "N2", north)
    held(tenant, "Culto A", central, 3, guests=2, present=[c1, c2, n1], registered=[c1, c2])
    held(tenant, "Culto B", central, 2, guests=4, present=[c1])
    held(tenant, "Culto Norte", north, 1, guests=5, present=[n1, c1], registered=[n1, n2])
    return central, north


@pytest.mark.django_db
class TestVisitors:
    def test_the_sheet_saves_a_visitor_count(self, authenticated_client, tenant):
        event = held(tenant, "Culto", days_ago=0)
        page = authenticated_client.get(reverse("event_attendance", args=[event.pk])).content.decode()
        assert 'name="guest_count"' in page

        authenticated_client.post(reverse("event_attendance", args=[event.pk]), {"guest_count": "12"})

        event.refresh_from_db()
        assert event.guest_count == 12 and event.total_attendance == 12

    def test_blank_or_nonsense_leaves_the_count_alone(self, authenticated_client, tenant):
        event = held(tenant, "Culto", days_ago=0, guests=7)
        for value in ("", "-3", "abc", "1.5"):
            authenticated_client.post(reverse("event_attendance", args=[event.pk]), {"guest_count": value})
            event.refresh_from_db()
            assert event.guest_count == 7, value

    def test_cannot_be_set_before_the_event_day(self, authenticated_client, tenant):
        event = Event.objects.create(tenant=tenant, title="Futuro", start_at=timezone.now() + timedelta(days=5))
        authenticated_client.post(reverse("event_attendance", args=[event.pk]), {"guest_count": "9"})
        event.refresh_from_db()
        assert event.guest_count == 0

    def test_the_total_is_members_plus_visitors(self, tenant):
        event = held(tenant, "Culto", guests=4, present=[person(tenant, "A"), person(tenant, "B")])
        assert event.total_attendance == 6

    def test_the_sheet_names_the_site_only_with_several_sites(self, authenticated_client, tenant, sites):
        _, north = sites
        event = held(tenant, "Culto Norte", north, days_ago=0)
        assert "Sede Norte" in authenticated_client.get(reverse("event_attendance", args=[event.pk])).content.decode()

    def test_the_api_exposes_and_validates_it(self, authenticated_api_client, tenant):
        event = held(tenant, "Culto", guests=3)
        got = authenticated_api_client.get(f"/api/v1/events/{event.pk}/").json()
        assert got["guest_count"] == 3
        assert authenticated_api_client.patch(
            f"/api/v1/events/{event.pk}/", {"guest_count": 8}, format="json"
        ).status_code == 200
        assert authenticated_api_client.patch(
            f"/api/v1/events/{event.pk}/", {"guest_count": -1}, format="json"
        ).status_code == 400


@pytest.mark.django_db
class TestReport:
    def test_summary_per_site(self, authenticated_client, scenario):
        context = authenticated_client.get(reverse("attendance_report")).context

        central, north = context["site_summary"]
        assert central["site"].name == "Sede principal" and north["site"].name == "Sede Norte"
        assert (central["events"], central["registered"], central["members"], central["guests"]) == (2, 2, 4, 6)
        assert (central["total"], central["average"], central["away"]) == (10, 5.0, 1)  # n1 is Norte's, at Central
        assert (north["events"], north["members"], north["guests"], north["total"]) == (1, 2, 5, 7)
        assert north["away"] == 1  # c1 is Central's, at Norte
        assert (context["total_events"], context["total_attendances"]) == (3, 6)
        assert (context["total_guests"], context["total_people"]) == (11, 17)

    def test_the_site_filter_narrows_everything(self, authenticated_client, scenario):
        _, north = scenario
        context = authenticated_client.get(reverse("attendance_report"), {"site": str(north.pk)}).context

        assert [e.title for e in context["event_rows"]] == ["Culto Norte"]
        assert [row["site"].name for row in context["site_summary"]] == ["Sede Norte"]
        assert context["total_people"] == 7
        names = {m.first_name for m in context["page"]}
        assert names == {"N1", "C1"}

    def test_a_bad_site_value_shows_nothing_instead_of_failing(self, authenticated_client, scenario):
        assert authenticated_client.get(reverse("attendance_report"), {"site": "xyz"}).status_code == 200

    def test_single_site_churches_do_not_get_the_site_ui(self, authenticated_client, tenant):
        held(tenant, "Culto", guests=3, present=[person(tenant, "A")])
        response = authenticated_client.get(reverse("attendance_report"))
        page = response.content.decode()
        assert "Resumen por sede" not in page and 'id="site"' not in page
        assert response.context["total_people"] == 4  # visitors still count

    def test_the_page_shows_summary_and_filter_with_several_sites(self, authenticated_client, scenario):
        page = authenticated_client.get(reverse("attendance_report")).content.decode()
        assert "Resumen por sede" in page and 'id="site"' in page and "Visitas" in page

    def test_export_and_pagination_links_keep_every_filter(self, authenticated_client, scenario):
        _, north = scenario
        page = authenticated_client.get(
            reverse("attendance_report"), {"site": str(north.pk), "type": "service"}
        ).content.decode()
        assert f"site={north.pk}" in page
        assert page.count("type=service") >= 3  # three export links
        assert "group=site" in page

    def test_still_restricted_to_member_managers(self, tenant):
        user = User.objects.create_user(
            email=f"t-{uuid.uuid4().hex[:6]}@t.com", password="x", role="treasurer", tenant=tenant
        )
        client = Client()
        client.force_login(user)
        assert client.get(reverse("attendance_report")).status_code == 403
        assert client.get(reverse("attendance_export"), {"group": "site"}).status_code == 403


@pytest.mark.django_db
class TestExports:
    def test_events_export_has_visitors_and_the_site_last(self, authenticated_client, scenario):
        rows = rows_of(authenticated_client.get(reverse("attendance_export"), {"kind": "events"}))

        assert rows[0] == ["Fecha", "Evento", "Tipo", "Inscritos", "Asistieron", "Visitas", "Sede"]
        by_title = {r[1]: r for r in rows[1:]}
        assert by_title["Culto Norte"][3:] == ["2", "2", "5", "Sede Norte"]
        assert by_title["Culto A"][3:] == ["2", "3", "2", "Sede principal"]

    def test_events_export_honours_the_site_filter(self, authenticated_client, scenario):
        _, north = scenario
        rows = rows_of(authenticated_client.get(reverse("attendance_export"), {"site": str(north.pk)}))
        assert [r[1] for r in rows[1:]] == ["Culto Norte"]

    def test_summary_export_by_site(self, authenticated_client, scenario):
        response = authenticated_client.get(reverse("attendance_export"), {"group": "site"})
        rows = rows_of(response)

        assert "asistencia-por-sede" in response["Content-Disposition"]
        assert rows[0] == [
            "Sede", "Eventos", "Inscritos", "Asistieron (miembros)", "Visitas", "Total de personas",
            "Promedio por evento", "Miembros de otra sede",
        ]
        assert rows[1] == ["Sede principal", "2", "2", "4", "6", "10", "5.0", "1"]
        assert rows[2] == ["Sede Norte", "1", "2", "2", "5", "7", "7.0", "1"]

    def test_the_members_export_is_unchanged(self, authenticated_client, scenario):
        rows = rows_of(authenticated_client.get(reverse("attendance_export"), {"kind": "members"}))
        assert rows[0] == ["Nombre", "Apellido", "Email", "Asistencias", "% de eventos", "Última asistencia"]
