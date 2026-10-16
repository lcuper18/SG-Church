"""
The e-mails: new-account link, password reset, donation receipt, event/course
confirmations and the block certificate. Mail goes to Django's in-memory outbox
(mail.outbox) in tests.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from education.models import Course, CourseBlock, Enrollment
from emails import notify
from emails.models import EmailLog
from emails.services import is_deliverable
from events.models import Event, EventRegistration
from finance.models import Donation
from members.models import Member, User

STRONG = "Clave-Segura-2026"


def _member(tenant, first="Ana", email=None, **kwargs):
    email = f"{first.lower()}@iglesia.org" if email is None else email
    return Member.objects.create(
        tenant=tenant, first_name=first, last_name="Mora", email=email, **kwargs
    )


def _links(message):
    return re.findall(r"https?://\S+", message.body)


def _can_log_in(email, password):
    response = Client().post(reverse("login"), {"login": email, "password": password})
    return response.status_code == 302 and response.url == "/dashboard/"


@pytest.mark.parametrize(
    "address,expected",
    [
        ("ana@iglesia.org", True),
        ("Ana.Mora@Gmail.com", True),
        ("", False),
        (None, False),
        ("sin-arroba", False),
        ("x@demo.sgchurch.test", False),   # the seeded demo people
        ("x@example.com", False),
        ("x@local.invalid", False),
        ("x@localhost", False),
    ],
)
def test_is_deliverable(address, expected):
    assert is_deliverable(address) is expected


@pytest.mark.django_db
class TestAccountCreated:
    def _create(self, client, **extra):
        data = {
            "first_name": "Suhellen", "last_name": "Fallas", "email": "suhellen@iglesia.org",
            "role": "treasurer", "password1": STRONG, "password2": STRONG, **extra,
        }
        return client.post(reverse("user_create"), data)

    def test_new_user_gets_an_email_without_the_typed_password(
        self, authenticated_client, admin_user
    ):
        self._create(authenticated_client)

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ["suhellen@iglesia.org"]
        assert admin_user.tenant.name in message.subject
        assert "Tesorero" in message.body
        assert STRONG not in message.body and STRONG not in message.alternatives[0][0]
        assert message.alternatives[0][1] == "text/html"

    def test_the_link_lets_them_choose_their_own_password(self, authenticated_client):
        self._create(authenticated_client)
        link = next(l for l in _links(mail.outbox[0]) if "/password/reset/key/" in l)

        client = Client()
        page = client.get(link, follow=True)
        assert page.status_code == 200 and "Elige tu contraseña" in page.content.decode()
        done = client.post(
            page.redirect_chain[-1][0] if page.redirect_chain else link,
            {"password1": "Mi-Propia-Clave-77", "password2": "Mi-Propia-Clave-77"},
            follow=True,
        )

        assert "Contraseña actualizada" in done.content.decode()
        assert _can_log_in("suhellen@iglesia.org", "Mi-Propia-Clave-77")

    def test_no_email_is_sent_when_validation_fails(self, authenticated_client):
        self._create(authenticated_client, password2="otra-distinta")

        assert mail.outbox == []

    def test_an_undeliverable_address_still_creates_the_user(self, authenticated_client):
        response = self._create(authenticated_client, email="x@demo.sgchurch.test")

        assert response.status_code == 302
        assert User.objects.filter(email="x@demo.sgchurch.test").exists()
        assert mail.outbox == []


@pytest.mark.django_db
class TestPasswordReset:
    """The 'Restablecer' link on the login page used to crash with
    NoReverseMatch (account_reset_password_from_key was never routed)."""

    def test_full_flow(self, admin_user):
        client = Client()
        response = client.post(reverse("account_reset_password"), {"email": admin_user.email})

        assert response.status_code == 302
        assert response.url == reverse("account_reset_password_done")
        assert "Revisa tu correo" in client.get(response.url).content.decode()
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == [admin_user.email]
        assert "Restablecer tu contraseña" in message.subject
        link = next(l for l in _links(message) if "/password/reset/key/" in l)

        page = client.get(link, follow=True)
        target = page.redirect_chain[-1][0] if page.redirect_chain else link
        done = client.post(
            target, {"password1": "Otra-Clave-Nueva-88", "password2": "Otra-Clave-Nueva-88"},
            follow=True,
        )
        assert "Contraseña actualizada" in done.content.decode()
        assert _can_log_in(admin_user.email, "Otra-Clave-Nueva-88")

    def test_unknown_email_gets_the_same_page_and_no_reset_link(self):
        """The response is identical (nobody can probe which addresses have an
        account); the address itself is told, in Spanish, that none exists."""
        response = Client().post(reverse("account_reset_password"), {"email": "nadie@iglesia.org"})

        assert response.status_code == 302 and response.url == reverse("account_reset_password_done")
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ["nadie@iglesia.org"]
        assert "no hay ninguna cuenta" in message.body
        assert "/password/reset/key/" not in message.body

    def test_a_bad_link_explains_itself(self):
        response = Client().get(
            reverse("account_reset_password_from_key", kwargs={"uidb36": "abc123", "key": "zzz-bad"}),
            follow=True,
        )

        assert response.status_code == 200
        assert "Enlace no válido" in response.content.decode()

    def test_the_login_page_link_works(self):
        assert Client().get(reverse("password_reset")).status_code == 200


@pytest.mark.django_db
class TestDonationReceipt:
    @pytest.fixture(autouse=True)
    def _church(self, admin_user):
        t = admin_user.tenant
        t.timezone, t.currency, t.email = "America/Costa_Rica", "CRC", "info@iglesia.org"
        t.save()

    def _donation(self, tenant, **kwargs):
        return Donation.objects.create(
            tenant=tenant, amount=Decimal("25000.00"), currency="CRC", status="completed",
            campaign="tithe", **kwargs,
        )

    def test_receipt_goes_to_the_donor_in_the_churchs_currency(self, admin_user):
        donation = self._donation(admin_user.tenant, donor_name="Don Pedro", donor_email="pedro@correo.com")

        assert notify.donation_receipt(donation) is True

        message = mail.outbox[0]
        assert message.to == ["pedro@correo.com"]
        assert "₡25\xa0000,00" in message.body and "Diezmo" in message.body
        assert "Don Pedro" in message.body
        assert message.reply_to == ["info@iglesia.org"]
        assert admin_user.tenant.name in message.from_email
        donation.refresh_from_db()
        assert donation.receipt_sent and donation.receipt_sent_at

    def test_uses_the_members_email_when_the_donor_gave_none(self, admin_user):
        ana = _member(admin_user.tenant, "Ana")
        donation = self._donation(admin_user.tenant, member=ana)

        notify.donation_receipt(donation)

        assert mail.outbox[0].to == ["ana@iglesia.org"] and "Ana Mora" in mail.outbox[0].body

    def test_no_address_no_email_and_not_marked_sent(self, admin_user):
        donation = self._donation(admin_user.tenant, donor_name="Anónimo")

        assert notify.donation_receipt(donation) is False

        assert mail.outbox == []
        donation.refresh_from_db()
        assert not donation.receipt_sent

    def test_the_stripe_webhook_path_sends_it(self, admin_user):
        from finance.views import handle_checkout_session

        handle_checkout_session({
            "metadata": {"tenant_id": str(admin_user.tenant.pk), "campaign": "offering",
                         "donor_name": "Lucía", "donor_email": "lucia@correo.com"},
            "amount_total": 1500, "currency": "usd", "payment_intent": "pi_1",
        })

        assert [m.to for m in mail.outbox] == [["lucia@correo.com"]]
        assert Donation.objects.get(donor_email="lucia@correo.com").receipt_sent

    def test_admins_get_their_in_app_notification_too(self, admin_user):
        """Creating it used to crash on the UUID id (an integer column) and, being
        in the same try block, silently skipped the receipt as well."""
        from finance.views import handle_checkout_session
        from notifications.models import Notification

        handle_checkout_session({
            "metadata": {"tenant_id": str(admin_user.tenant.pk), "donor_email": "lucia@correo.com"},
            "amount_total": 1500, "currency": "usd", "payment_intent": "pi_2",
        })

        donation = Donation.objects.get(donor_email="lucia@correo.com")
        notification = Notification.objects.get(user=admin_user)
        assert notification.object_id == str(donation.pk)
        assert len(mail.outbox) == 1

    def test_a_failing_notification_does_not_skip_the_receipt(self, admin_user):
        from finance.views import handle_checkout_session

        with mock.patch("notifications.models.create_notification", side_effect=RuntimeError("x")):
            handle_checkout_session({
                "metadata": {"tenant_id": str(admin_user.tenant.pk), "donor_email": "lucia@correo.com"},
                "amount_total": 1500, "currency": "usd", "payment_intent": "pi_3",
            })

        assert len(mail.outbox) == 1

    def test_the_receipt_no_longer_claims_a_tax_status(self, admin_user):
        notify.donation_receipt(self._donation(admin_user.tenant, donor_email="p@correo.com"))

        assert "501" not in mail.outbox[0].alternatives[0][0]


@pytest.mark.django_db
class TestEventRegistrationEmail:
    @pytest.fixture
    def event(self, admin_user):
        admin_user.tenant.timezone = "America/Costa_Rica"
        admin_user.tenant.save()
        return Event.objects.create(
            tenant=admin_user.tenant, title="Retiro de jóvenes", location="Centro de retiros",
            # 01:00 UTC on the 21st is 19:00 on the 20th in Costa Rica
            start_at=datetime(2030, 10, 21, 1, 0, tzinfo=dt_timezone.utc),
        )

    def _register(self, client, event, member):
        return client.post(reverse("registration_create", args=[event.pk]), {"member": str(member.pk)})

    def test_registering_confirms_by_email_in_the_churchs_time(
        self, authenticated_client, admin_user, event
    ):
        ana = _member(admin_user.tenant, "Ana")

        self._register(authenticated_client, event, ana)

        message = mail.outbox[0]
        assert message.to == ["ana@iglesia.org"]
        assert "Retiro de jóvenes" in message.subject
        assert "20 de octubre de 2030, 19:00" in message.body
        assert "Centro de retiros" in message.body
        assert "/events/" in message.body  # link back to the event

    def test_nothing_is_sent_when_registration_is_refused(
        self, authenticated_client, admin_user, event
    ):
        event.requires_baptized = True
        event.save()

        self._register(authenticated_client, event, _member(admin_user.tenant, "Ana"))

        assert mail.outbox == []

    def test_a_member_without_email_is_still_registered(
        self, authenticated_client, admin_user, event
    ):
        beto = _member(admin_user.tenant, "Beto", email="")

        self._register(authenticated_client, event, beto)

        assert mail.outbox == []
        assert EventRegistration.objects.filter(member=beto, event=event).exists()

    def test_the_api_confirms_too(self, authenticated_api_client, admin_user, event):
        ana = _member(admin_user.tenant, "Ana")

        response = authenticated_api_client.post(
            "/api/v1/event-registrations/", {"member": ana.pk, "event": event.pk}
        )

        assert response.status_code == 201 and len(mail.outbox) == 1


@pytest.mark.django_db
class TestCourseEmails:
    @pytest.fixture
    def block(self, admin_user):
        return CourseBlock.objects.create(tenant=admin_user.tenant, name="Discipulado")

    def _course(self, tenant, title, block=None):
        return Course.objects.create(tenant=tenant, title=title, course_block=block)

    def test_enrolling_confirms_by_email_and_mentions_the_block(
        self, authenticated_client, admin_user, block
    ):
        course = self._course(admin_user.tenant, "Fundamentos", block)
        ana = _member(admin_user.tenant, "Ana")

        authenticated_client.post(
            reverse("enrollment_create", args=[course.pk]), {"member": str(ana.pk)}
        )

        message = mail.outbox[0]
        assert message.to == ["ana@iglesia.org"] and "Fundamentos" in message.subject
        assert "Discipulado" in message.body and "certificado" in message.body

    def test_a_refused_enrollment_sends_nothing(self, authenticated_client, admin_user):
        course = Course.objects.create(
            tenant=admin_user.tenant, title="Solo bautizados", requires_baptized=True
        )

        authenticated_client.post(
            reverse("enrollment_create", args=[course.pk]),
            {"member": str(_member(admin_user.tenant, "Ana").pk)},
        )

        assert mail.outbox == []

    def test_the_certificate_is_emailed_once_when_the_block_is_finished(
        self, authenticated_client, admin_user, block
    ):
        tenant = admin_user.tenant
        ana = _member(tenant, "Ana")
        first, second = self._course(tenant, "Uno", block), self._course(tenant, "Dos", block)
        enrollments = [
            Enrollment.objects.create(tenant=tenant, member=ana, course=c) for c in (first, second)
        ]
        complete = lambda e: authenticated_client.post(reverse("enrollment_complete", args=[e.pk]))

        complete(enrollments[0])
        assert mail.outbox == []  # block not finished yet

        complete(enrollments[1])
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert "Tu certificado" in message.subject and "CERT-" in message.body
        assert "/education/certificates/" in message.body

        complete(enrollments[1])  # pressing the button again
        assert len(mail.outbox) == 1

    def test_the_api_path_emails_the_certificate_too(
        self, authenticated_api_client, admin_user, block
    ):
        tenant = admin_user.tenant
        ana = _member(tenant, "Ana")
        only = self._course(tenant, "Unico", block)
        enrollment = Enrollment.objects.create(tenant=tenant, member=ana, course=only)

        response = authenticated_api_client.patch(
            f"/api/v1/enrollments/{enrollment.pk}/", {"status": "completed"}
        )

        assert response.status_code == 200
        assert [m.subject for m in mail.outbox] == [f"Tu certificado: {block.name}"]


@pytest.mark.django_db
class TestDeliveryProblemsNeverBreakTheAction:
    def test_smtp_failure_is_logged_and_the_registration_still_works(
        self, authenticated_client, admin_user
    ):
        event = Event.objects.create(
            tenant=admin_user.tenant, title="Culto", start_at=timezone.now() + timedelta(days=2)
        )
        ana = _member(admin_user.tenant, "Ana")

        with mock.patch("emails.services.EmailMultiAlternatives.send", side_effect=OSError("SMTP down")):
            response = authenticated_client.post(
                reverse("registration_create", args=[event.pk]), {"member": str(ana.pk)}
            )

        assert response.status_code == 302
        assert EventRegistration.objects.filter(member=ana, event=event).exists()
        log = EmailLog.objects.get(to_email="ana@iglesia.org")
        assert log.status == "failed" and "SMTP down" in log.error_message

    def test_successful_sends_are_logged(self, authenticated_client, admin_user):
        event = Event.objects.create(
            tenant=admin_user.tenant, title="Culto", start_at=timezone.now() + timedelta(days=2)
        )
        authenticated_client.post(
            reverse("registration_create", args=[event.pk]),
            {"member": str(_member(admin_user.tenant, "Ana").pk)},
        )

        log = EmailLog.objects.get(to_email="ana@iglesia.org")
        assert log.status == "sent" and log.tenant == admin_user.tenant and log.sent_at

    def test_when_celery_is_down_the_mail_goes_out_inline(self, admin_user):
        ana = _member(admin_user.tenant, "Ana")
        event = Event.objects.create(
            tenant=admin_user.tenant, title="Culto", start_at=timezone.now() + timedelta(days=2)
        )
        registration = EventRegistration.objects.create(tenant=admin_user.tenant, member=ana, event=event)

        with mock.patch("emails.tasks.send_logged_email_task.delay", side_effect=ConnectionError("no broker")):
            assert notify.event_registration(registration) is True

        assert len(mail.outbox) == 1
        assert EmailLog.objects.get(to_email="ana@iglesia.org").status == "sent"

    def test_a_template_error_cannot_raise_out_of_notify(self, admin_user):
        ana = _member(admin_user.tenant, "Ana")

        with mock.patch("emails.notify.render_email", side_effect=RuntimeError("boom")):
            assert notify.queue_email(ana.email, "x", "event_registration", {}, admin_user.tenant) is False
