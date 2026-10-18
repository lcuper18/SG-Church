"""
Automatic reminders: 1 day and 1 hour before each event, only to the people
registered, never twice, never for events/people that arrived inside the window.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from events import reminders
from events.models import Event, EventNotification, EventRegistration
from events.tasks import send_event_reminders
from members.models import Member

HOUR = timedelta(hours=1)


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


def make_event(tenant, start_in, **kwargs):
    """An event starting `start_in` from now that was created long ago."""
    event = Event.objects.create(
        tenant=tenant, title=kwargs.pop("title", "Culto"), start_at=timezone.now() + start_in, **kwargs
    )
    Event.objects.filter(pk=event.pk).update(created_at=timezone.now() - timedelta(days=30))
    event.refresh_from_db()
    return event


def register(event, name="Ana", email=None, ago=timedelta(days=10)):
    member = Member.objects.create(
        tenant=event.tenant, first_name=name, last_name="Pérez",
        email=email if email is not None else f"{name.lower()}@iglesia.org",
    )
    registration = EventRegistration.objects.create(tenant=event.tenant, member=member, event=event)
    EventRegistration.objects.filter(pk=registration.pk).update(registered_at=timezone.now() - ago)
    return member


@pytest.mark.django_db
class TestWindows:
    def test_day_before_goes_out_once_the_event_is_24h_away(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        register(event)
        assert reminders.send_due_reminders() == 1
        assert len(mail.outbox) == 1
        assert "es mañana" in mail.outbox[0].subject
        assert EventNotification.objects.get().kind == "day_before"

    def test_nothing_before_the_window_opens(self, tenant):
        register(make_event(tenant, 30 * HOUR))
        assert reminders.send_due_reminders() == 0
        assert mail.outbox == []

    def test_hour_before(self, tenant):
        register(make_event(tenant, timedelta(minutes=50)))
        assert reminders.send_due_reminders() == 1
        assert "empieza pronto" in mail.outbox[0].subject
        assert EventNotification.objects.get().kind == "hour_before"

    def test_running_again_never_duplicates(self, tenant):
        register(make_event(tenant, 23 * HOUR))
        reminders.send_due_reminders()
        assert reminders.send_due_reminders() == 0
        assert len(mail.outbox) == 1

    def test_a_late_worker_still_catches_up_but_not_stale_ones(self, tenant):
        # 19h away: the 24h mark passed 5h ago (inside the 6h grace) -> still sent.
        register(make_event(tenant, 19 * HOUR, title="Reciente"))
        # 15h away: passed 9h ago (beyond the grace) -> not sent.
        register(make_event(tenant, 15 * HOUR, title="Viejo"), name="Beto")
        assert reminders.send_due_reminders() == 1
        assert "Reciente" in mail.outbox[0].subject

    def test_both_reminders_in_sequence(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        register(event)
        reminders.send_due_reminders()
        reminders.send_due_reminders(now=timezone.now() + 22 * HOUR + timedelta(minutes=10))
        assert sorted(EventNotification.objects.values_list("kind", flat=True)) == ["day_before", "hour_before"]
        assert len(mail.outbox) == 2

    def test_the_task_is_registered_and_runs(self, tenant):
        register(make_event(tenant, 23 * HOUR))
        assert send_event_reminders() == 1


@pytest.mark.django_db
class TestWhoGetsIt:
    def test_only_registered_people(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        register(event, "Ana")
        Member.objects.create(tenant=tenant, first_name="Otro", last_name="X", email="otro@iglesia.org")
        cancelled = register(event, "Cora")
        EventRegistration.objects.filter(member=cancelled).update(status="cancelled")
        reminders.send_due_reminders()
        assert [m.to for m in mail.outbox] == [["ana@iglesia.org"]]

    def test_no_reminder_for_someone_who_registered_inside_the_window(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        register(event, "Tarde", ago=timedelta(minutes=5))
        assert reminders.send_due_reminders() == 0

    def test_no_reminder_for_an_event_created_inside_the_window(self, tenant):
        event = Event.objects.create(tenant=tenant, title="Nuevo", start_at=timezone.now() + 23 * HOUR)
        register(event)
        assert reminders.send_due_reminders() == 0

    def test_undeliverable_address_is_recorded_as_skipped(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        register(event, "Demo", email="demo@demo.sgchurch.test")
        assert reminders.send_due_reminders() == 0
        assert EventNotification.objects.get().status == "skipped"
        assert mail.outbox == []

    def test_member_without_email_is_skipped(self, tenant):
        register(make_event(tenant, 23 * HOUR), "Sin", email="")
        assert reminders.send_due_reminders() == 0
        assert EventNotification.objects.get().status == "skipped"

    def test_deleted_member_gets_nothing(self, tenant):
        member = register(make_event(tenant, 23 * HOUR))
        member.delete()
        assert reminders.send_due_reminders() == 0

    def test_inactive_trashed_and_opted_out_events_are_ignored(self, tenant):
        for kwargs in ({"is_active": False}, {"reminders_enabled": False}):
            register(make_event(tenant, 23 * HOUR, **kwargs), name=f"P{len(kwargs)}{list(kwargs)[0][:3]}")
        gone = make_event(tenant, 23 * HOUR)
        register(gone, "Borrado")
        gone.delete()
        assert reminders.send_due_reminders() == 0

    def test_batch_limit_leaves_the_rest_for_the_next_run(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        for index in range(5):
            register(event, f"Nombre{chr(65 + index)}")
        assert reminders.send_due_reminders(batch=3) == 3
        assert reminders.send_due_reminders(batch=3) == 2
        assert len(mail.outbox) == 5


@pytest.mark.django_db
class TestContent:
    def test_the_time_is_shown_in_the_church_time_zone(self, tenant):
        tenant.timezone = "America/Costa_Rica"
        tenant.save()
        event = make_event(tenant, 23 * HOUR)
        Event.objects.filter(pk=event.pk).update(
            start_at=timezone.now().replace(minute=0, second=0, microsecond=0) + 23 * HOUR
        )
        event.refresh_from_db()
        register(event)
        reminders.send_due_reminders()
        local = timezone.localtime(event.start_at, timezone.zoneinfo.ZoneInfo("America/Costa_Rica"))
        assert local.strftime("%H:%M") in mail.outbox[0].body

    def test_the_site_is_named_when_the_church_has_several(self, tenant):
        from tenants.models import Site

        Site.objects.create(tenant=tenant, name="Sede Norte", address="Calle 5")
        event = make_event(tenant, 23 * HOUR, site=tenant.sites.get(name="Sede Norte"))
        register(event)
        reminders.send_due_reminders()
        assert "Sede Norte" in mail.outbox[0].body


@pytest.mark.django_db
class TestRearming:
    def _sent(self, tenant):
        event = make_event(tenant, 23 * HOUR)
        register(event)
        reminders.send_due_reminders()
        assert EventNotification.objects.count() == 1
        return Event.objects.get(pk=event.pk)

    def test_moving_the_event_more_than_an_hour_starts_over(self, tenant):
        event = self._sent(tenant)
        event.start_at += timedelta(hours=3)
        event.save()
        assert EventNotification.objects.count() == 0

    def test_a_small_change_keeps_the_ledger(self, tenant):
        event = self._sent(tenant)
        event.start_at += timedelta(minutes=30)
        event.save()
        assert EventNotification.objects.count() == 1


@pytest.mark.django_db
class TestForm:
    def test_toggle_off_from_the_form(self, authenticated_client, tenant):
        event = make_event(tenant, 5 * 24 * HOUR)
        assert event.reminders_enabled is True
        data = {
            "title": event.title, "event_type": "other", "is_active": "on",
            "start_at": timezone.localtime(event.start_at).strftime("%Y-%m-%dT%H:%M"),
        }
        response = authenticated_client.post(reverse("event_update", args=[event.pk]), data)
        assert response.status_code == 302
        event.refresh_from_db()
        assert event.reminders_enabled is False

    def test_new_events_default_to_on(self, authenticated_client):
        response = authenticated_client.get(reverse("event_create"))
        assert 'name="reminders_enabled" checked' in response.content.decode()

    def test_detail_shows_the_state(self, authenticated_client, tenant):
        event = make_event(tenant, 5 * 24 * HOUR)
        assert "1 día y 1 hora antes" in authenticated_client.get(reverse("event_detail", args=[event.pk])).content.decode()

    def test_beat_schedule_has_the_task(self):
        from django.conf import settings

        assert settings.CELERY_BEAT_SCHEDULE["event-reminders"]["task"] == "events.tasks.send_event_reminders"
