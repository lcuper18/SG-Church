"""
Repeating events: the date maths (incl. daylight-saving), creating a series from
the form, editing/cancelling/deleting "this" or "this and the following".
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from education.models import Course
from events import recurrence
from events.models import Event, EventAttendance, EventRegistration, EventSeries
from members.models import Member, User

NY = ZoneInfo("America/New_York")
UTC = dt_timezone.utc
FIRST = date(2030, 5, 1)  # a Wednesday


def local(value):
    return timezone.localtime(value, NY)


def form_data(**overrides):
    data = {
        "title": "Culto de miércoles", "event_type": "service", "location": "Templo",
        "start_at": "2030-05-01T19:00", "end_at": "2030-05-01T21:00", "is_active": "on",
        "repeat": "on", "repeat_end": "weeks", "repeat_weeks": "4",
    }
    data.update(overrides)
    return data


@pytest.fixture
def tenant(admin_user):
    admin_user.tenant.timezone = "America/New_York"
    admin_user.tenant.save()
    return admin_user.tenant


def create_series_via_form(client, **overrides):
    response = client.post(reverse("event_create"), form_data(**overrides))
    assert response.status_code == 302, getattr(response, "context", None) and response.context["form"].errors
    return list(Event.objects.filter(series__isnull=False).order_by("start_at"))


class TestDateMaths:
    def test_weeks_and_weekdays(self):
        dates, until = recurrence.occurrence_dates(FIRST, {2, 4}, weeks=3)  # Wed + Fri
        assert dates == [date(2030, 5, 1), date(2030, 5, 3), date(2030, 5, 8), date(2030, 5, 10),
                         date(2030, 5, 15), date(2030, 5, 17)]
        assert until == date(2030, 5, 21)

    def test_until_date(self):
        dates, until = recurrence.occurrence_dates(FIRST, {2}, until_date=date(2030, 5, 22))
        assert [d.day for d in dates] == [1, 8, 15, 22] and until == date(2030, 5, 22)

    @pytest.mark.parametrize(
        "kwargs, fragment",
        [
            ({"weekdays": set(), "weeks": 2}, "al menos un día"),
            ({"weekdays": {9}, "weeks": 2}, "no válidos"),
            ({"weekdays": {2}}, "hasta cuándo"),
            ({"weekdays": {2}, "until_date": date(2030, 4, 1)}, "anterior"),
            ({"weekdays": {2}, "until_date": date(2032, 1, 1)}, "más de un año"),
            ({"weekdays": {0, 1, 2}, "weeks": 30}, "máximo es 52"),
            ({"weekdays": {0}, "until_date": date(2030, 5, 1)}, "ningún evento"),
        ],
    )
    def test_invalid_repetitions_explain_themselves(self, kwargs, fragment):
        with pytest.raises(recurrence.RecurrenceError, match=fragment):
            recurrence.occurrence_dates(FIRST, **kwargs)

    def test_exactly_the_cap_is_allowed(self):
        dates, _ = recurrence.occurrence_dates(FIRST, {2}, weeks=52)
        assert len(dates) == 52

    def test_the_wall_clock_hour_survives_daylight_saving(self):
        before = recurrence.localize(date(2030, 11, 2), time(19, 0), NY)  # still EDT
        after = recurrence.localize(date(2030, 11, 9), time(19, 0), NY)   # EST
        assert before == datetime(2030, 11, 2, 23, 0, tzinfo=UTC)
        assert after == datetime(2030, 11, 10, 0, 0, tzinfo=UTC)
        assert local(before).hour == local(after).hour == 19

    def test_a_time_that_does_not_exist_moves_to_the_first_valid_one(self):
        gap = recurrence.localize(date(2030, 3, 10), time(2, 30), NY)  # clocks jump 2:00 -> 3:00
        assert local(gap).time() == time(3, 30)

    def test_an_ambiguous_time_takes_the_first_occurrence(self):
        first = recurrence.localize(date(2030, 11, 3), time(1, 30), NY)
        assert first == datetime(2030, 11, 3, 5, 30, tzinfo=UTC)  # 1:30 EDT, not EST

    def test_windows(self):
        start, end = recurrence.window(FIRST, time(17, 0), time(22, 0), NY)
        assert (local(start).hour, local(end).hour, local(end).date()) == (17, 22, FIRST)
        start, end = recurrence.window(FIRST, time(22, 0), time(1, 0), NY)  # ends after midnight
        assert local(end).date() == FIRST + timedelta(days=1)
        assert recurrence.window(FIRST, time(17, 0), None, NY)[1] is None


@pytest.mark.django_db
class TestCreatingASeries:
    def test_a_weekly_series_becomes_one_event_per_date(self, authenticated_client, tenant, admin_user):
        course = Course.objects.create(tenant=tenant, title="Fe")
        events = create_series_via_form(authenticated_client, required_courses=[str(course.pk)])

        assert len(events) == 4
        assert {e.series_id for e in events} == {events[0].series_id}
        assert [local(e.start_at).day for e in events] == [1, 8, 15, 22]
        assert all(local(e.start_at).hour == 19 and local(e.end_at).hour == 21 for e in events)
        assert all(e.original_start_at == e.start_at and e.title == "Culto de miércoles" for e in events)
        assert all(e.site == tenant.main_site() and list(e.required_courses.all()) == [course] for e in events)
        series = events[0].series
        assert (series.weekdays, series.start_time, series.end_time, series.created_by) == (
            [2], time(19, 0), time(21, 0), admin_user,
        )
        assert series.weekday_names == ["miércoles"]

    def test_several_weekdays_and_the_first_day_is_always_included(self, authenticated_client):
        events = create_series_via_form(authenticated_client, repeat_weekdays=["4", "6"], repeat_weeks="2")
        assert [local(e.start_at).strftime("%a %d") for e in events] == [
            "Wed 01", "Fri 03", "Sun 05", "Wed 08", "Fri 10", "Sun 12",
        ]

    def test_until_a_date(self, authenticated_client):
        events = create_series_via_form(authenticated_client, repeat_end="until", repeat_until="2030-05-15")
        assert [local(e.start_at).day for e in events] == [1, 8, 15]

    def test_the_hour_holds_across_the_clock_change(self, authenticated_client):
        events = create_series_via_form(
            authenticated_client, start_at="2030-10-30T19:00", end_at="2030-10-30T21:00", repeat_weeks="3"
        )
        assert [local(e.start_at).hour for e in events] == [19, 19, 19]
        assert events[0].start_at.hour != events[2].start_at.hour  # UTC moved, the wall clock didn't

    def test_an_event_that_ends_after_midnight(self, authenticated_client):
        events = create_series_via_form(authenticated_client, start_at="2030-05-01T22:00", end_at="2030-05-02T01:00")
        assert local(events[0].end_at).date() == date(2030, 5, 2)
        assert all(e.end_at - e.start_at == timedelta(hours=3) for e in events[:3])

    def test_no_end_time_is_fine(self, authenticated_client):
        events = create_series_via_form(authenticated_client, end_at="")
        assert all(e.end_at is None for e in events)

    def test_the_site_is_kept(self, authenticated_client, tenant):
        from tenants.models import Site

        north = Site.objects.create(tenant=tenant, name="Norte")
        events = create_series_via_form(authenticated_client, site=str(north.pk))
        assert {e.site_id for e in events} == {north.pk} and events[0].series.site == north

    @pytest.mark.parametrize(
        "overrides, fragment",
        [
            ({"repeat_weeks": "60"}, "Máximo"),  # field limit
            ({"repeat_weekdays": ["0", "1", "2", "3", "4", "5", "6"], "repeat_weeks": "9"}, "máximo es 52"),
            ({"repeat_weeks": ""}, "hasta cuándo"),
            ({"start_at": "2020-01-01T10:00", "end_at": ""}, "en el futuro"),
            ({"end_at": "2030-05-01T18:00"}, "posterior al inicio"),
        ],
    )
    def test_bad_requests_create_nothing_and_say_why(self, authenticated_client, overrides, fragment):
        response = authenticated_client.post(reverse("event_create"), form_data(**overrides))
        assert response.status_code == 200
        assert not Event.objects.exists() and not EventSeries.objects.exists()
        assert fragment.lower() in response.content.decode().lower()

    def test_without_repeat_it_is_a_normal_single_event(self, authenticated_client):
        data = form_data()
        del data["repeat"]
        authenticated_client.post(reverse("event_create"), data)
        event = Event.objects.get()
        assert event.series is None and event.original_start_at is None

    def test_the_same_slot_cannot_exist_twice(self, authenticated_client):
        events = create_series_via_form(authenticated_client)
        with pytest.raises(IntegrityError), transaction.atomic():
            Event.objects.create(
                tenant=events[0].tenant, title="Duplicado", start_at=events[0].start_at,
                series=events[0].series, original_start_at=events[0].original_start_at,
            )

    def test_the_form_offers_repeat_only_when_creating(self, authenticated_client, tenant):
        assert 'id="repeat"' in authenticated_client.get(reverse("event_create")).content.decode()
        event = Event.objects.create(tenant=tenant, title="Solo", start_at=timezone.now() + timedelta(days=2))
        assert 'id="repeat"' not in authenticated_client.get(reverse("event_update", args=[event.pk])).content.decode()

    def test_every_occurrence_is_audited(self, authenticated_client, admin_user):
        from core.models import AuditLog

        create_series_via_form(authenticated_client)
        entries = AuditLog.objects.filter(model_label="events.event", action="create")
        assert entries.count() == 4 and set(entries.values_list("user_id", flat=True)) == {admin_user.pk}


@pytest.fixture
def series(authenticated_client, tenant):
    return create_series_via_form(authenticated_client, repeat_weeks="5")


def edit(client, event, **changes):
    data = {
        "title": event.title, "event_type": event.event_type, "location": event.location,
        "start_at": local(event.start_at).strftime("%Y-%m-%dT%H:%M"),
        "end_at": local(event.end_at).strftime("%Y-%m-%dT%H:%M") if event.end_at else "",
        "is_active": "on" if event.is_active else "",
    }
    data.update(changes)
    if data["is_active"] == "":
        del data["is_active"]
    return client.post(reverse("event_update", args=[event.pk]), data)


@pytest.mark.django_db
class TestEditingASeries:
    def test_this_only_changes_one_event(self, authenticated_client, series):
        edit(authenticated_client, series[1], title="Culto especial", edit_scope="this")
        titles = [e.title for e in Event.objects.filter(series=series[0].series).order_by("start_at")]
        assert titles == ["Culto de miércoles", "Culto especial"] + ["Culto de miércoles"] * 3

    def test_following_changes_this_and_the_next_but_not_the_earlier_ones(self, authenticated_client, series):
        edit(authenticated_client, series[2], title="Nuevo nombre", edit_scope="following")
        titles = [e.title for e in Event.objects.filter(series__isnull=False).order_by("start_at")]
        assert titles == ["Culto de miércoles"] * 2 + ["Nuevo nombre"] * 3

    def test_following_only_applies_what_was_actually_changed(self, authenticated_client, series):
        Event.objects.filter(pk=series[3].pk).update(location="Salón anexo")  # edited by hand earlier
        edit(authenticated_client, series[2], title="Nuevo nombre", edit_scope="following")
        later = Event.objects.get(pk=series[3].pk)
        assert later.title == "Nuevo nombre" and later.location == "Salón anexo"

        edit(authenticated_client, Event.objects.get(pk=series[2].pk), location="Templo principal", edit_scope="following")
        assert Event.objects.get(pk=series[3].pk).location == "Templo principal"

    def test_a_new_time_is_applied_to_each_events_own_date(self, authenticated_client, series):
        Event.objects.filter(pk=series[3].pk).update(  # this one was moved to Thursday
            start_at=series[3].start_at + timedelta(days=1), end_at=series[3].end_at + timedelta(days=1)
        )
        edit(
            authenticated_client, series[2],
            start_at="2030-05-15T18:30", end_at="2030-05-15T20:00", edit_scope="following",
        )
        moved = Event.objects.get(pk=series[3].pk)
        assert (local(moved.start_at).strftime("%a %H:%M"), local(moved.end_at).strftime("%H:%M")) == ("Thu 18:30", "20:00")
        assert local(Event.objects.get(pk=series[4].pk).start_at).strftime("%H:%M") == "18:30"
        assert local(Event.objects.get(pk=series[1].pk).start_at).strftime("%H:%M") == "19:00"  # earlier: untouched

    def test_the_series_is_split_so_the_old_rule_keeps_the_past(self, authenticated_client, series):
        original = series[0].series
        edit(authenticated_client, series[2], start_at="2030-05-15T18:30", end_at="2030-05-15T20:00", edit_scope="following")

        old = EventSeries.objects.get(pk=original.pk)
        new = Event.objects.get(pk=series[2].pk).series
        assert new.pk != old.pk
        assert (old.until_date, old.start_time) == (date(2030, 5, 14), time(19, 0))
        assert (new.first_date, new.start_time, new.end_time) == (date(2030, 5, 15), time(18, 30), time(20, 0))
        assert {e.series_id for e in Event.objects.filter(pk__in=[s.pk for s in series[2:]])} == {new.pk}
        assert {e.series_id for e in Event.objects.filter(pk__in=[s.pk for s in series[:2]])} == {old.pk}

    def test_editing_from_the_first_occurrence_does_not_split(self, authenticated_client, series):
        edit(authenticated_client, series[0], title="Todos", edit_scope="following")
        assert EventSeries.objects.count() == 1
        assert {e.title for e in Event.objects.filter(series__isnull=False)} == {"Todos"}

    def test_occurrences_with_attendance_or_in_the_past_are_left_alone(self, authenticated_client, tenant, series):
        member = Member.objects.create(tenant=tenant, first_name="A", last_name="B")
        EventAttendance.objects.create(tenant=tenant, member=member, event=series[3])

        edit(authenticated_client, series[1], title="Cambiado", edit_scope="following")

        assert Event.objects.get(pk=series[3].pk).title == "Culto de miércoles"  # attendance already taken
        assert Event.objects.get(pk=series[2].pk).title == "Cambiado"

    def test_required_courses_follow_only_when_changed(self, authenticated_client, tenant, series):
        course = Course.objects.create(tenant=tenant, title="Fe")
        edit(authenticated_client, series[1], title="Otro", edit_scope="following")
        assert not Event.objects.get(pk=series[2].pk).required_courses.exists()
        edit(authenticated_client, Event.objects.get(pk=series[1].pk), required_courses=[str(course.pk)], edit_scope="following")
        assert list(Event.objects.get(pk=series[3].pk).required_courses.all()) == [course]

    def test_registrations_survive_a_time_change(self, authenticated_client, tenant, series):
        member = Member.objects.create(tenant=tenant, first_name="A", last_name="B")
        EventRegistration.objects.create(tenant=tenant, member=member, event=series[3])
        edit(authenticated_client, series[2], start_at="2030-05-15T18:00", end_at="", edit_scope="following")
        assert Event.objects.get(pk=series[3].pk).registrations.count() == 1


@pytest.mark.django_db
class TestCancellingAndDeleting:
    def registered(self, tenant, event, email="ana@iglesia.org"):
        member = Member.objects.create(tenant=tenant, first_name="Ana", last_name=email[:3], email=email)
        EventRegistration.objects.create(tenant=tenant, member=member, event=event)
        return member

    def test_cancel_this_only(self, authenticated_client, series):
        authenticated_client.post(reverse("event_cancel", args=[series[1].pk]), {"scope": "this"})
        assert [e.is_active for e in Event.objects.filter(series__isnull=False).order_by("start_at")] == [
            True, False, True, True, True,
        ]

    def test_cancel_following(self, authenticated_client, series):
        authenticated_client.post(reverse("event_cancel", args=[series[2].pk]), {"scope": "following"})
        assert [e.is_active for e in Event.objects.filter(series__isnull=False).order_by("start_at")] == [
            True, True, False, False, False,
        ]

    def test_following_skips_occurrences_that_already_have_attendance(self, authenticated_client, tenant, series):
        member = Member.objects.create(tenant=tenant, first_name="A", last_name="B")
        EventAttendance.objects.create(tenant=tenant, member=member, event=series[3])
        authenticated_client.post(reverse("event_cancel", args=[series[2].pk]), {"scope": "following"})
        assert Event.objects.get(pk=series[3].pk).is_active and not Event.objects.get(pk=series[4].pk).is_active

    def test_the_registered_are_told_only_when_asked(self, authenticated_client, tenant, series):
        self.registered(tenant, series[1])
        self.registered(tenant, series[1], email="beto@iglesia.org")
        Member.objects.create(tenant=tenant, first_name="Sin", last_name="Correo")  # not registered
        mail.outbox.clear()

        authenticated_client.post(reverse("event_cancel", args=[series[0].pk]), {"scope": "this"})
        assert mail.outbox == []

        response = authenticated_client.post(
            reverse("event_cancel", args=[series[1].pk]), {"scope": "this", "notify": "on"}, follow=True
        )
        assert sorted(m.to[0] for m in mail.outbox) == ["ana@iglesia.org", "beto@iglesia.org"]
        assert "Evento cancelado" in mail.outbox[0].subject
        assert "Se avisó a 2 persona(s)" in response.content.decode()

    def test_a_cancelled_event_can_be_switched_back_on(self, authenticated_client, series):
        authenticated_client.post(reverse("event_cancel", args=[series[1].pk]), {"scope": "this"})
        event = Event.objects.get(pk=series[1].pk)
        edit(authenticated_client, event, is_active="on", edit_scope="this")
        assert Event.objects.get(pk=series[1].pk).is_active

    def test_non_series_events_ignore_the_following_scope(self, authenticated_client, tenant):
        events = [Event.objects.create(tenant=tenant, title=f"E{i}", start_at=timezone.now() + timedelta(days=i + 1)) for i in range(2)]
        authenticated_client.post(reverse("event_cancel", args=[events[0].pk]), {"scope": "following"})
        assert [Event.objects.get(pk=e.pk).is_active for e in events] == [False, True]

    def test_delete_this_or_following_goes_to_the_trash(self, authenticated_client, series):
        authenticated_client.post(reverse("event_delete", args=[series[1].pk]), {"scope": "this"})
        assert Event.objects.filter(series__isnull=False).count() == 4
        authenticated_client.post(reverse("event_delete", args=[series[3].pk]), {"scope": "following"})
        assert Event.objects.filter(series__isnull=False).count() == 2
        assert Event.all_objects.filter(series__isnull=False, deleted_at__isnull=False).count() == 3

    def test_the_pages_offer_the_scope_only_for_series(self, authenticated_client, tenant, series):
        for name in ("event_cancel", "event_delete"):
            page = authenticated_client.get(reverse(name, args=[series[0].pk])).content.decode()
            assert 'value="following"' in page
        single = Event.objects.create(tenant=tenant, title="Solo", start_at=timezone.now() + timedelta(days=2))
        assert 'value="following"' not in authenticated_client.get(reverse("event_cancel", args=[single.pk])).content.decode()

    def test_permissions(self, tenant, series):
        user = User.objects.create_user(email=f"m-{uuid.uuid4().hex[:6]}@t.com", password="x", role="member", tenant=tenant)
        client = Client()
        client.force_login(user)
        assert client.get(reverse("event_cancel", args=[series[0].pk])).status_code == 403
        assert client.post(reverse("event_cancel", args=[series[0].pk]), {"scope": "this"}).status_code == 403
        assert Client().get(reverse("event_cancel", args=[series[0].pk])).status_code == 302

    def test_other_churches_events_are_untouchable(self, authenticated_client, series):
        from tenants.models import Tenant

        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        foreign = Event.objects.create(tenant=other, title="Ajeno", start_at=timezone.now() + timedelta(days=2))
        assert authenticated_client.post(reverse("event_cancel", args=[foreign.pk]), {}).status_code == 404


@pytest.mark.django_db
class TestDisplay:
    def test_list_and_detail_show_the_series(self, authenticated_client, series):
        listing = authenticated_client.get(reverse("event_list")).content.decode()
        assert "Parte de una serie" in listing
        detail = authenticated_client.get(reverse("event_detail", args=[series[0].pk])).content.decode()
        assert "Cada miércoles" in detail and "Cancelar evento" in detail

    def test_a_cancelled_event_is_marked(self, authenticated_client, series):
        authenticated_client.post(reverse("event_cancel", args=[series[0].pk]), {"scope": "this"})
        detail = authenticated_client.get(reverse("event_detail", args=[series[0].pk])).content.decode()
        assert "Cancelado" in detail and "Cancelar evento" not in detail
