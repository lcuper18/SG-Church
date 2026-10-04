"""
Web tests for taking attendance and the attendance report.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Event, EventAttendance, EventRegistration
from members.models import Member


@pytest.fixture
def past_event(db, admin_user):
    return Event.objects.create(
        tenant=admin_user.tenant, title="Culto", start_at=timezone.now() - timedelta(days=1)
    )


def _members(admin_user, n=3):
    return [
        Member.objects.create(tenant=admin_user.tenant, first_name=f"M{i}", last_name="Test")
        for i in range(n)
    ]


@pytest.mark.django_db
class TestTakeAttendance:
    def test_page_lists_members_and_marks_registered(
        self, authenticated_client, admin_user, past_event
    ):
        a, b, _ = _members(admin_user)
        EventRegistration.objects.create(tenant=admin_user.tenant, member=a, event=past_event)

        html = authenticated_client.get(f"/events/{past_event.pk}/attendance/").content.decode()

        assert str(a.pk) in html and str(b.pk) in html
        assert html.count("Inscrito") == 1

    def test_save_marks_any_member_registered_or_not(
        self, authenticated_client, admin_user, past_event
    ):
        a, b, c = _members(admin_user)
        EventRegistration.objects.create(tenant=admin_user.tenant, member=a, event=past_event)

        authenticated_client.post(
            f"/events/{past_event.pk}/attendance/",
            {"shown": [str(a.pk), str(b.pk), str(c.pk)], "present": [str(a.pk), str(c.pk)]},
        )

        present = set(past_event.attendances.values_list("member_id", flat=True))
        assert present == {a.pk, c.pk}  # c never registered, still counts

    def test_unchecking_removes_attendance(self, authenticated_client, admin_user, past_event):
        a, _, _ = _members(admin_user)
        EventAttendance.objects.create(tenant=admin_user.tenant, member=a, event=past_event)

        authenticated_client.post(
            f"/events/{past_event.pk}/attendance/", {"shown": [str(a.pk)]}
        )

        assert past_event.attendances.count() == 0

    def test_saving_a_filtered_list_keeps_hidden_members(
        self, authenticated_client, admin_user, past_event
    ):
        a, b, _ = _members(admin_user)
        EventAttendance.objects.create(tenant=admin_user.tenant, member=a, event=past_event)

        # Only b was on screen (search filter); a must stay marked.
        authenticated_client.post(
            f"/events/{past_event.pk}/attendance/",
            {"shown": [str(b.pk)], "present": [str(b.pk)]},
        )

        assert set(past_event.attendances.values_list("member_id", flat=True)) == {a.pk, b.pk}

    def test_search_filters_the_list(self, authenticated_client, admin_user, past_event):
        a, b, _ = _members(admin_user)

        html = authenticated_client.get(
            f"/events/{past_event.pk}/attendance/?q=M1"
        ).content.decode()

        assert str(b.pk) in html and str(a.pk) not in html

    def test_cannot_save_before_event_day(self, authenticated_client, admin_user):
        future = Event.objects.create(
            tenant=admin_user.tenant, title="Futuro", start_at=timezone.now() + timedelta(days=9)
        )
        a, _, _ = _members(admin_user)

        authenticated_client.post(
            f"/events/{future.pk}/attendance/", {"shown": [str(a.pk)], "present": [str(a.pk)]}
        )

        assert future.attendances.count() == 0

    def test_ignores_members_of_other_tenants(
        self, authenticated_client, admin_user, past_event, tenant
    ):
        foreign = Member.objects.create(tenant=tenant, first_name="Otra", last_name="Iglesia")

        authenticated_client.post(
            f"/events/{past_event.pk}/attendance/",
            {"shown": [str(foreign.pk)], "present": [str(foreign.pk)]},
        )

        assert past_event.attendances.count() == 0

    def test_member_role_is_forbidden(self, regular_client_same_tenant, past_event):
        response = regular_client_same_tenant.get(f"/events/{past_event.pk}/attendance/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAttendanceReport:
    def test_report_counts_per_event_and_member(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        a, b, _ = _members(admin_user)
        events = [
            Event.objects.create(
                tenant=tenant, title=f"Culto {i}", start_at=timezone.now() - timedelta(days=i + 1)
            )
            for i in range(4)
        ]
        for e in events[:3]:
            EventAttendance.objects.create(tenant=tenant, member=a, event=e)
        EventAttendance.objects.create(tenant=tenant, member=b, event=events[0])

        response = authenticated_client.get("/events/attendance/report/")
        html = response.content.decode()

        assert response.status_code == 200
        assert response.context["total_events"] == 4
        assert response.context["total_attendances"] == 4
        rows = list(response.context["page"])
        assert [(r.first_name, r.attended, r.percent) for r in rows] == [("M0", 3, 75), ("M1", 1, 25)]
        assert "M0" in html

    def test_report_respects_date_range_and_type(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        Event.objects.create(
            tenant=tenant, title="Viejo", event_type="retreat",
            start_at=timezone.now() - timedelta(days=200),
        )
        Event.objects.create(
            tenant=tenant, title="Reciente", event_type="service",
            start_at=timezone.now() - timedelta(days=5),
        )

        default = authenticated_client.get("/events/attendance/report/")
        assert default.context["total_events"] == 1  # last 90 days only

        by_type = authenticated_client.get(
            "/events/attendance/report/?start=2000-01-01&type=retreat"
        )
        assert by_type.context["total_events"] == 1
        assert [r.title for r in by_type.context["event_rows"]] == ["Viejo"]

    def test_report_ignores_bad_dates(self, authenticated_client):
        response = authenticated_client.get("/events/attendance/report/?start=nope&end=also-bad")
        assert response.status_code == 200

    def test_report_requires_members_permission(self, regular_client_same_tenant):
        assert regular_client_same_tenant.get("/events/attendance/report/").status_code == 403


@pytest.mark.django_db
class TestEventPagesShowAttendance:
    def test_detail_shows_attended_and_no_shows(self, authenticated_client, admin_user, past_event):
        a, b, _ = _members(admin_user)
        for member in (a, b):
            EventRegistration.objects.create(tenant=admin_user.tenant, member=member, event=past_event)
        EventAttendance.objects.create(tenant=admin_user.tenant, member=a, event=past_event)

        response = authenticated_client.get(f"/events/{past_event.pk}/")
        html = response.content.decode()

        assert response.status_code == 200
        assert response.context["attended_count"] == 1
        assert response.context["no_show_count"] == 1
        assert "Tomar asistencia" in html

    def test_list_links_to_report(self, authenticated_client):
        html = authenticated_client.get("/events/").content.decode()
        assert "/events/attendance/report/" in html

    def test_member_role_does_not_see_attendance_button(
        self, regular_client_same_tenant, past_event
    ):
        html = regular_client_same_tenant.get(f"/events/{past_event.pk}/").content.decode()
        assert "Tomar asistencia" not in html
