"""
seed_demo_data backfills requirements onto demo events created before the
plan had any (the seed skips events that already exist), and removes the
registrations/attendances of members who no longer qualify.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from events.models import Event, EventAttendance, EventRegistration
from members.models import Member


def _member(tenant, name, **kwargs):
    return Member.objects.create(
        tenant=tenant, first_name=name, last_name="Demo",
        email=f"{name.lower()}@demo.sgchurch.test", **kwargs,
    )


@pytest.fixture
def seeded(tenant):
    """A tenant that looks already seeded, with requirement-less plan events."""
    baptized = _member(tenant, "Bautizada", is_baptized=True, marital_status="single")
    pagan = _member(tenant, "Nuevo", is_baptized=False, marital_status="single")
    past = Event.objects.create(
        tenant=tenant, title="Retiro de damas", start_at=timezone.now() - timedelta(days=45)
    )
    future = Event.objects.create(
        tenant=tenant, title="Conferencia de misiones", start_at=timezone.now() + timedelta(days=50)
    )
    free = Event.objects.create(
        tenant=tenant, title="Culto dominical", start_at=timezone.now() + timedelta(days=7)
    )
    for ev in (past, future, free):
        for m in (baptized, pagan):
            EventRegistration.objects.create(tenant=tenant, member=m, event=ev)
    for m in (baptized, pagan):
        EventAttendance.objects.create(tenant=tenant, member=m, event=past)
    return tenant, baptized, pagan, past, future, free


@pytest.mark.django_db
class TestEventRequirementsBackfill:
    def test_applies_requirements_and_drops_ineligible_people(self, seeded):
        tenant, baptized, pagan, past, future, free = seeded

        call_command("seed_demo_data", tenant=tenant.subdomain)

        for ev in (past, future):
            ev.refresh_from_db()
            assert ev.requires_baptized
            assert list(ev.registrations.values_list("member_id", flat=True)) == [baptized.pk]
        assert list(past.attendances.values_list("member_id", flat=True)) == [baptized.pk]

    def test_events_without_rules_in_the_plan_are_untouched(self, seeded):
        tenant, *_, free = seeded

        call_command("seed_demo_data", tenant=tenant.subdomain)

        free.refresh_from_db()
        assert not free.requires_baptized and not free.requires_married
        assert free.registrations.count() == 2

    def test_is_idempotent_and_respects_hand_edited_events(self, seeded):
        tenant, baptized, pagan, past, future, free = seeded
        future.requires_married = True  # an admin already chose different rules
        future.save(update_fields=["requires_married"])

        call_command("seed_demo_data", tenant=tenant.subdomain)
        call_command("seed_demo_data", tenant=tenant.subdomain)

        future.refresh_from_db()
        assert future.requires_married and not future.requires_baptized
        assert future.registrations.count() == 2
        assert past.registrations.count() == 1
