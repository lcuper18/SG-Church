"""
Unsubscribing from reminders and announcements: the signed link, the one-click
POST, the headers and footer, and that opted-out people are really left out.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from emails import notify
from emails.unsubscribe import make_token, member_for
from events import announcements, reminders
from events.models import Event, EventAnnouncement, EventRegistration
from members.models import Member

SITE = "https://iglesia.example.org"


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def ana(tenant):
    return Member.objects.create(tenant=tenant, first_name="Ana", last_name="Pérez", email="ana@iglesia.org")


@pytest.fixture
def event(tenant, ana):
    event = Event.objects.create(tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(hours=23))
    Event.objects.filter(pk=event.pk).update(created_at=timezone.now() - timedelta(days=30))
    registration = EventRegistration.objects.create(tenant=tenant, member=ana, event=event)
    EventRegistration.objects.filter(pk=registration.pk).update(registered_at=timezone.now() - timedelta(days=9))
    return Event.objects.get(pk=event.pk)


def link(member):
    return reverse("email_unsubscribe", args=[make_token(member)])


@pytest.mark.django_db
class TestPage:
    def test_a_get_never_changes_anything(self, client, ana):
        response = client.get(link(ana))
        assert response.status_code == 200 and "Dejar de recibir recordatorios" in response.content.decode()
        ana.refresh_from_db()
        assert ana.email_opt_out is False

    def test_post_unsubscribes_without_logging_in(self, client, ana):
        response = client.post(link(ana), {"action": "unsubscribe"})
        assert "Ya no recibirás" in response.content.decode()
        ana.refresh_from_db()
        assert ana.email_opt_out is True

    def test_one_click_post_from_a_mail_app(self, ana):
        client = Client(enforce_csrf_checks=True)
        client.post(link(ana), "List-Unsubscribe=One-Click", content_type="application/x-www-form-urlencoded")
        ana.refresh_from_db()
        assert ana.email_opt_out is True

    def test_can_come_back(self, client, ana):
        client.post(link(ana), {"action": "unsubscribe"})
        assert "Ya no recibes" in client.get(link(ana)).content.decode()
        client.post(link(ana), {"action": "resubscribe"})
        ana.refresh_from_db()
        assert ana.email_opt_out is False

    def test_forged_or_tampered_links_do_nothing(self, client, ana):
        for token in ("nonsense", make_token(ana)[:-3] + "xxx"):
            response = client.post(reverse("email_unsubscribe", args=[token]), {"action": "unsubscribe"})
            assert response.status_code == 404
        ana.refresh_from_db()
        assert ana.email_opt_out is False

    def test_a_deleted_member_gives_an_invalid_link(self, client, ana):
        token = make_token(ana)
        ana.delete()
        assert member_for(token) is None
        assert client.get(reverse("email_unsubscribe", args=[token])).status_code == 404


@pytest.mark.django_db
class TestEmails:
    @pytest.fixture(autouse=True)
    def site_url(self, settings):
        settings.SITE_URL = SITE

    def test_reminders_carry_the_link_and_headers(self, event):
        reminders.send_due_reminders()
        message = mail.outbox[0]
        assert f"{SITE}/email/unsubscribe/" in message.body
        assert message.extra_headers["List-Unsubscribe"].startswith(f"<{SITE}/email/unsubscribe/")
        assert message.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
        assert "Dejar de recibir recordatorios y anuncios" in message.alternatives[0][0]

    def test_announcements_carry_it_too(self, tenant, event):
        EventAnnouncement.objects.create(tenant=tenant, event=event, subject="Hola", body="Texto")
        announcements.send_due()
        assert f"{SITE}/email/unsubscribe/" in mail.outbox[0].body

    def test_the_link_in_the_mail_works(self, client, event, ana):
        reminders.send_due_reminders()
        path = mail.outbox[0].extra_headers["List-Unsubscribe"].strip("<>").replace(SITE, "")
        client.post(path, {"action": "unsubscribe"})
        ana.refresh_from_db()
        assert ana.email_opt_out is True

    def test_transactional_mail_has_no_link(self, tenant, ana, event):
        registration = EventRegistration.objects.get(member=ana)
        notify.event_registration(registration)
        assert "unsubscribe" not in mail.outbox[0].body

    def test_without_a_site_address_there_is_simply_no_link(self, event, settings):
        settings.SITE_URL = ""
        reminders.send_due_reminders()
        assert "unsubscribe" not in mail.outbox[0].body
        assert not mail.outbox[0].extra_headers.get("List-Unsubscribe")


@pytest.mark.django_db
class TestOptedOutPeopleAreLeftOut:
    def test_no_reminders(self, event, ana):
        Member.objects.filter(pk=ana.pk).update(email_opt_out=True)
        assert reminders.send_due_reminders() == 0 and mail.outbox == []

    def test_no_announcements_and_they_are_not_counted(self, authenticated_client, tenant, event, ana):
        Member.objects.filter(pk=ana.pk).update(email_opt_out=True)
        data = {"subject": "Aviso", "body": "Texto", "audience": "registered", "when": "now"}
        response = authenticated_client.post(reverse("announcement_create", args=[event.pk]), data, follow=True)
        assert "No hay a quién enviarlo" in response.content.decode()
        assert mail.outbox == []

    def test_cancellation_notices_still_go_out(self, event, ana):
        Member.objects.filter(pk=ana.pk).update(email_opt_out=True)
        assert notify.event_cancelled(event) == 1


@pytest.mark.django_db
class TestWhereItIsSet:
    def test_a_member_can_do_it_from_their_own_record(self, client, tenant, ana, regular_user_same_tenant):
        regular_user = regular_user_same_tenant
        regular_user.member_profile = ana
        regular_user.save()
        client.force_login(regular_user)
        data = {"phone": "", "address": "", "city": "", "state": "", "postal_code": "", "email_opt_out": "on"}
        client.post(reverse("my_record_edit"), data)
        ana.refresh_from_db()
        assert ana.email_opt_out is True

    def test_staff_can_record_a_request_from_the_member_form(self, authenticated_client, ana):
        response = authenticated_client.get(reverse("member_update", args=[ana.pk]))
        assert 'name="email_opt_out"' in response.content.decode()
        assert "email_opt_out" in authenticated_client.get("/api/v1/members/").content.decode()
