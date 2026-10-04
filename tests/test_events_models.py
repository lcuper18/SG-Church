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


@pytest.mark.django_db
class TestRequirements:
    def test_blocked_by_baptism_requirement(self, event, plain_member):
        event.requires_baptized = True
        event.save()

        allowed, reason = event.can_register(plain_member)

        assert allowed is False
        assert "bautizado" in reason

    def test_allowed_once_baptized(self, event, plain_member):
        event.requires_baptized = True
        event.save()
        plain_member.is_baptized = True
        plain_member.save(update_fields=["is_baptized"])

        assert event.can_register(plain_member)[0] is True

    def test_blocked_by_marriage_requirement(self, event, plain_member):
        event.requires_married = True
        event.save()

        allowed, reason = event.can_register(plain_member)

        assert allowed is False
        assert "casado" in reason

    def test_allowed_once_married(self, event, plain_member):
        event.requires_married = True
        event.save()
        plain_member.marital_status = "married"
        plain_member.save(update_fields=["marital_status"])

        assert event.can_register(plain_member)[0] is True

    def test_blocked_by_missing_required_course(self, tenant, event, plain_member):
        from education.models import Course

        course = Course.objects.create(tenant=tenant, title="Liderazgo")
        event.required_courses.add(course)

        allowed, reason = event.can_register(plain_member)

        assert allowed is False
        assert "Liderazgo" in reason

    def test_course_only_enrolled_does_not_satisfy(self, tenant, event, plain_member):
        from education.models import Course, Enrollment

        course = Course.objects.create(tenant=tenant, title="Liderazgo")
        event.required_courses.add(course)
        Enrollment.objects.create(
            tenant=tenant, member=plain_member, course=course, status="enrolled"
        )

        assert event.can_register(plain_member)[0] is False

    def test_allowed_after_completing_required_course(self, tenant, event, plain_member):
        from education.models import Course, Enrollment

        course = Course.objects.create(tenant=tenant, title="Liderazgo")
        event.required_courses.add(course)
        Enrollment.objects.create(
            tenant=tenant, member=plain_member, course=course, status="completed"
        )

        assert event.can_register(plain_member)[0] is True

    def test_meets_requirements_ignores_dates_and_capacity(self, tenant, plain_member):
        past_full = Event.objects.create(
            tenant=tenant,
            title="Old",
            start_at=timezone.now() - timedelta(days=3),
            capacity=0,
            requires_baptized=True,
        )
        plain_member.is_baptized = True
        plain_member.save(update_fields=["is_baptized"])

        assert past_full.meets_requirements(plain_member) == (True, "")
        assert past_full.can_register(plain_member)[0] is False
