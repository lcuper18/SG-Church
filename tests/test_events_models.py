"""
Model-level tests for the events app: registration eligibility rules.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Event, EventRegistration
from members.models import Member


@pytest.fixture
def event(db, tenant):
    return Event.objects.create(
        tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=7)
    )


@pytest.fixture
def plain_member(db, tenant):
    return Member.objects.create(tenant=tenant, first_name="Plain", last_name="Member")


@pytest.mark.django_db
class TestCanRegister:
    def test_allowed_for_open_upcoming_event(self, event, plain_member):
        assert event.can_register(plain_member) == (True, "")

    def test_blocked_when_inactive(self, event, plain_member):
        event.is_active = False
        event.save()
        allowed, _ = event.can_register(plain_member)
        assert allowed is False

    def test_blocked_when_past(self, tenant, plain_member):
        past = Event.objects.create(
            tenant=tenant, title="Old", start_at=timezone.now() - timedelta(days=2)
        )
        allowed, reason = past.can_register(plain_member)
        assert allowed is False
        assert "finalizó" in reason

    def test_blocked_when_capacity_full(self, tenant, event, plain_member):
        event.capacity = 1
        event.save()
        other = Member.objects.create(tenant=tenant, first_name="Other", last_name="One")
        EventRegistration.objects.create(tenant=tenant, member=other, event=event)

        allowed, reason = event.can_register(plain_member)

        assert allowed is False
        assert "capacidad" in reason

    def test_cancelled_registration_frees_capacity(self, tenant, event, plain_member):
        event.capacity = 1
        event.save()
        other = Member.objects.create(tenant=tenant, first_name="Other", last_name="One")
        EventRegistration.objects.create(
            tenant=tenant, member=other, event=event, status="cancelled"
        )

        assert event.can_register(plain_member)[0] is True

    def test_blocked_when_already_registered(self, tenant, event, plain_member):
        EventRegistration.objects.create(tenant=tenant, member=plain_member, event=event)

        allowed, reason = event.can_register(plain_member)

        assert allowed is False
        assert "ya está inscrito" in reason

    def test_allowed_again_after_cancelling(self, tenant, event, plain_member):
        EventRegistration.objects.create(
            tenant=tenant, member=plain_member, event=event, status="cancelled"
        )
        assert event.can_register(plain_member)[0] is True
