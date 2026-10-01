"""
Model-level tests for the education app: eligibility checks, prerequisites,
enrollment lifecycle, and block-certificate issuance.
"""

import pytest

from education.models import BlockCertificate, Enrollment
from members.models import Member


@pytest.fixture
def plain_member(db, tenant):
    """A member with no sacraments/marital status set, for requirement tests."""
    return Member.objects.create(
        tenant=tenant, first_name="Plain", last_name="Member"
    )


@pytest.mark.django_db
class TestCanEnroll:
    def test_blocked_by_baptism_requirement(self, course_factory, plain_member):
        course = course_factory(requires_baptized=True)

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is False
        assert "bautizado" in reason

    def test_allowed_once_baptized(self, course_factory, plain_member):
        course = course_factory(requires_baptized=True)
        plain_member.is_baptized = True
        plain_member.save(update_fields=["is_baptized"])

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is True
        assert reason == ""

    def test_blocked_by_marriage_requirement(self, course_factory, plain_member):
        course = course_factory(requires_married=True)

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is False
        assert "casado" in reason

    def test_allowed_once_married(self, course_factory, plain_member):
        course = course_factory(requires_married=True)
        plain_member.marital_status = "married"
        plain_member.save(update_fields=["marital_status"])

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is True

    def test_blocked_by_missing_prerequisite(self, course_factory, plain_member):
        prereq = course_factory(title="Prerequisite Course")
        course = course_factory(title="Advanced Course")
        course.prerequisite_courses.add(prereq)

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is False
        assert "Prerequisite Course" in reason

    def test_allowed_after_prerequisite_completed(self, course_factory, plain_member):
        prereq = course_factory(title="Prerequisite Course")
        course = course_factory(title="Advanced Course")
        course.prerequisite_courses.add(prereq)

        Enrollment.objects.create(
            tenant=prereq.tenant,
            member=plain_member,
            course=prereq,
            status="completed",
        )

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is True

    def test_blocked_when_capacity_full(self, course_factory, tenant):
        course = course_factory(capacity=1)
        existing_member = Member.objects.create(
            tenant=tenant, first_name="Existing", last_name="Member"
        )
        Enrollment.objects.create(
            tenant=tenant, member=existing_member, course=course, status="enrolled"
        )
        new_member = Member.objects.create(
            tenant=tenant, first_name="New", last_name="Member"
        )

        allowed, reason = course.can_enroll(new_member)

        assert allowed is False
        assert "capacidad" in reason

    def test_dropped_enrollment_frees_capacity(self, course_factory, tenant):
        course = course_factory(capacity=1)
        existing_member = Member.objects.create(
            tenant=tenant, first_name="Existing", last_name="Member"
        )
        Enrollment.objects.create(
            tenant=tenant, member=existing_member, course=course, status="dropped"
        )
        new_member = Member.objects.create(
            tenant=tenant, first_name="New", last_name="Member"
        )

        allowed, reason = course.can_enroll(new_member)

        assert allowed is True

    def test_blocked_when_already_enrolled(self, course_factory, plain_member):
        course = course_factory()
        Enrollment.objects.create(
            tenant=course.tenant, member=plain_member, course=course, status="enrolled"
        )

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is False
        assert "ya está inscrito" in reason

    def test_blocked_when_inactive(self, course_factory, plain_member):
        course = course_factory(is_active=False)

        allowed, reason = course.can_enroll(plain_member)

        assert allowed is False


@pytest.mark.django_db
class TestEnrollmentCompletion:
    def test_mark_completed_sets_status_and_timestamp(self, course_factory, plain_member):
        course = course_factory()
        enrollment = Enrollment.objects.create(
            tenant=course.tenant, member=plain_member, course=course
        )

        enrollment.mark_completed()
        enrollment.refresh_from_db()

        assert enrollment.status == "completed"
        assert enrollment.completed_at is not None

    def test_independent_course_completion_does_not_create_certificate(
        self, course_factory, plain_member
    ):
        course = course_factory()  # no course_block
        enrollment = Enrollment.objects.create(
            tenant=course.tenant, member=plain_member, course=course
        )

        certificate = enrollment.mark_completed()

        assert certificate is None
        assert BlockCertificate.objects.count() == 0


@pytest.mark.django_db
class TestBlockCertificate:
    def test_completing_all_block_courses_issues_certificate(
        self, course_factory, course_block_factory, plain_member
    ):
        block = course_block_factory()
        course_a = course_factory(title="Course A", course_block=block)
        course_b = course_factory(title="Course B", course_block=block)

        enrollment_a = Enrollment.objects.create(
            tenant=block.tenant, member=plain_member, course=course_a
        )
        enrollment_b = Enrollment.objects.create(
            tenant=block.tenant, member=plain_member, course=course_b
        )

        assert enrollment_a.mark_completed() is None  # block not finished yet
        certificate = enrollment_b.mark_completed()

        assert certificate is not None
        assert certificate.member == plain_member
        assert certificate.course_block == block
        assert certificate.certificate_number.startswith("CERT-")
        assert BlockCertificate.objects.filter(
            member=plain_member, course_block=block
        ).count() == 1

    def test_does_not_double_issue_certificate(
        self, course_factory, course_block_factory, plain_member
    ):
        block = course_block_factory()
        course = course_factory(title="Only Course", course_block=block)
        enrollment = Enrollment.objects.create(
            tenant=block.tenant, member=plain_member, course=course
        )

        first = enrollment.mark_completed()
        second = block.check_and_issue_certificate(plain_member)

        assert first is not None
        assert second.pk == first.pk
        assert BlockCertificate.objects.filter(
            member=plain_member, course_block=block
        ).count() == 1
