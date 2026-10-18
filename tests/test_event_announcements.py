"""
Custom announcements: audience (registered / tag), now or scheduled, cancelling,
idempotent delivery, and the rules around the event.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from events import announcements
from events.models import Event, EventAnnouncement, EventNotification, EventRegistration
from members.models import Member, Tag

DAY = timedelta(days=1)


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def event(tenant):
    return Event.objects.create(
        tenant=tenant, title="Retiro", start_at=timezone.now() + 3 * DAY, end_at=timezone.now() + 3 * DAY + timedelta(hours=3)
    )


def person(tenant, name, email=True):
    return Member.objects.create(
        tenant=tenant, first_name=name, last_name="Gómez", email=f"{name.lower()}@iglesia.org" if email else ""
    )


def register(event, member):
    EventRegistration.objects.create(tenant=event.tenant, member=member, event=event)


def announce(event, **kwargs):
    data = {"subject": "Traer biblia", "body": "No olviden\nla biblia.", "audience": "registered", "when": "now"}
    data.update(kwargs)
    return data


def post(client, event, **kwargs):
    return client.post(reverse("announcement_create", args=[event.pk]), announce(event, **kwargs), follow=True)


@pytest.mark.django_db
class TestSendNow:
    def test_goes_to_the_people_registered(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        register(event, person(tenant, "Beto"))
        person(tenant, "Cora")  # not registered
        post(authenticated_client, event)
        assert sorted(m.to[0] for m in mail.outbox) == ["ana@iglesia.org", "beto@iglesia.org"]
        assert mail.outbox[0].subject == "Traer biblia"
        assert "la biblia" in mail.outbox[0].body
        item = EventAnnouncement.objects.get()
        assert (item.status, item.recipient_count) == ("sent", 2)

    def test_to_a_tag_even_if_not_registered(self, authenticated_client, tenant, event):
        tag = Tag.objects.create(tenant=tenant, name="Jóvenes")
        ana = person(tenant, "Ana")
        ana.tags.add(tag)
        person(tenant, "Beto")
        post(authenticated_client, event, audience="tag", tag=str(tag.pk))
        assert [m.to[0] for m in mail.outbox] == ["ana@iglesia.org"]

    def test_tag_of_another_church_is_refused(self, authenticated_client, event):
        from tenants.models import Tenant

        other = Tenant.objects.create(name="Otra", subdomain="otra-x")
        tag = Tag.objects.create(tenant=other, name="Ajena")
        post(authenticated_client, event, audience="tag", tag=str(tag.pk))
        assert EventAnnouncement.objects.count() == 0 and mail.outbox == []

    def test_nobody_to_send_to_creates_nothing(self, authenticated_client, event):
        response = post(authenticated_client, event)
        assert "No hay a quién enviarlo" in response.content.decode()
        assert EventAnnouncement.objects.count() == 0

    def test_over_the_cap_is_refused(self, authenticated_client, tenant, event, monkeypatch):
        monkeypatch.setattr(EventAnnouncement, "MAX_RECIPIENTS", 1)
        register(event, person(tenant, "Ana"))
        register(event, person(tenant, "Beto"))
        response = post(authenticated_client, event)
        assert "el máximo por anuncio" in response.content.decode()
        assert EventAnnouncement.objects.count() == 0

    def test_not_for_a_cancelled_or_finished_event(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        Event.objects.filter(pk=event.pk).update(is_active=False)
        post(authenticated_client, event)
        assert EventAnnouncement.objects.count() == 0

    def test_a_plain_member_cannot_announce(self, regular_client, event):
        response = regular_client.post(reverse("announcement_create", args=[event.pk]), announce(event))
        assert response.status_code in (302, 403)
        assert EventAnnouncement.objects.count() == 0


@pytest.mark.django_db
class TestScheduled:
    def later(self, hours):
        return (timezone.localtime() + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")

    def test_waits_until_its_time(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        post(authenticated_client, event, when="later", send_at=self.later(5))
        item = EventAnnouncement.objects.get()
        assert item.status == "scheduled" and mail.outbox == []
        assert announcements.send_due() == 0
        assert announcements.send_due(now=timezone.now() + timedelta(hours=6)) == 1
        assert len(mail.outbox) == 1
        item.refresh_from_db()
        assert item.status == "sent"

    def test_past_date_or_after_the_event_is_refused(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        post(authenticated_client, event, when="later", send_at=self.later(-2))
        post(authenticated_client, event, when="later", send_at=self.later(24 * 10))
        post(authenticated_client, event, when="later")
        assert EventAnnouncement.objects.count() == 0

    def test_can_be_cancelled_while_waiting(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        post(authenticated_client, event, when="later", send_at=self.later(5))
        item = EventAnnouncement.objects.get()
        authenticated_client.post(reverse("announcement_cancel", args=[item.pk]))
        item.refresh_from_db()
        assert item.status == "cancelled"
        assert announcements.send_due(now=timezone.now() + timedelta(hours=6)) == 0
        assert mail.outbox == []

    def test_cannot_cancel_after_sending(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        post(authenticated_client, event)
        item = EventAnnouncement.objects.get()
        authenticated_client.post(reverse("announcement_cancel", args=[item.pk]))
        item.refresh_from_db()
        assert item.status == "sent"

    def test_skipped_if_the_event_was_cancelled_meanwhile(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        post(authenticated_client, event, when="later", send_at=self.later(5))
        Event.objects.filter(pk=event.pk).update(is_active=False)
        announcements.send_due(now=timezone.now() + timedelta(hours=6))
        assert EventAnnouncement.objects.get().status == "skipped" and mail.outbox == []


@pytest.mark.django_db
class TestDelivery:
    def make(self, tenant, event, **kwargs):
        return EventAnnouncement.objects.create(
            tenant=tenant, event=event, subject="Aviso", body="Texto", audience="registered", **kwargs
        )

    def test_two_announcements_to_the_same_person_both_arrive(self, tenant, event):
        register(event, person(tenant, "Ana"))
        self.make(tenant, event)
        self.make(tenant, event)
        announcements.send_due()
        assert len(mail.outbox) == 2

    def test_an_interrupted_send_resumes_without_repeating(self, tenant, event):
        ana, beto = person(tenant, "Ana"), person(tenant, "Beto")
        register(event, ana)
        register(event, beto)
        item = self.make(tenant, event, status="sending")
        EventNotification.objects.create(
            tenant=tenant, event=event, member=ana, kind="announcement", announcement=item
        )
        EventAnnouncement.objects.filter(pk=item.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        assert announcements.send_due() == 1
        assert [m.to[0] for m in mail.outbox] == ["beto@iglesia.org"]
        item.refresh_from_db()
        assert item.status == "sent"

    def test_a_fresh_sending_one_is_left_alone(self, tenant, event):
        register(event, person(tenant, "Ana"))
        self.make(tenant, event, status="sending")
        assert announcements.send_due() == 0

    def test_undeliverable_addresses_are_skipped(self, tenant, event):
        member = person(tenant, "Demo")
        Member.objects.filter(pk=member.pk).update(email="demo@demo.sgchurch.test")
        register(event, member)
        item = self.make(tenant, event)
        announcements.send_due()
        item.refresh_from_db()
        assert item.recipient_count == 0 and mail.outbox == []

    def test_the_beat_task_also_sends_announcements(self, tenant, event):
        from events.tasks import send_event_reminders

        register(event, person(tenant, "Ana"))
        self.make(tenant, event)
        send_event_reminders()
        assert len(mail.outbox) == 1

    def test_reminders_and_announcements_do_not_clash_in_the_ledger(self, tenant, event):
        ana = person(tenant, "Ana")
        register(event, ana)
        EventNotification.objects.create(tenant=tenant, event=event, member=ana, kind="day_before")
        self.make(tenant, event)
        announcements.send_due()
        assert len(mail.outbox) == 1


@pytest.mark.django_db
class TestPage:
    def test_the_detail_lists_them(self, authenticated_client, tenant, event):
        register(event, person(tenant, "Ana"))
        post(authenticated_client, event)
        html = authenticated_client.get(reverse("event_detail", args=[event.pk])).content.decode()
        assert "Traer biblia" in html and "Enviado" in html and 'id="announce-form"' in html
