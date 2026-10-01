"""
Integration Tests: Education (Courses) API
"""

import pytest
from rest_framework import status


@pytest.mark.integration
@pytest.mark.django_db
class TestCoursesAPI:
    """Test cases for Courses API."""

    def test_course_list_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/courses/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_course_list_authenticated(self, authenticated_api_client, admin_user):
        from education.models import Course

        Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = authenticated_api_client.get("/api/v1/courses/")
        assert response.status_code == status.HTTP_200_OK

    def test_course_list_only_own_tenant(self, authenticated_api_client, admin_user):
        from tenants.models import Tenant
        from education.models import Course

        Course.objects.create(tenant=admin_user.tenant, title="Own Tenant Course")
        other_tenant = Tenant.objects.create(
            name="Other Church", subdomain="othercourseschurch", is_active=True
        )
        Course.objects.create(tenant=other_tenant, title="Other Tenant Course")

        response = authenticated_api_client.get("/api/v1/courses/")

        if hasattr(response, "data") and "results" in response.data:
            assert len(response.data["results"]) == 1

    def test_course_create(self, authenticated_api_client):
        data = {"title": "New Course"}
        response = authenticated_api_client.post("/api/v1/courses/", data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_course_retrieve(self, authenticated_api_client, admin_user):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = authenticated_api_client.get(f"/api/v1/courses/{course.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == course.title

    def test_course_update(self, authenticated_api_client, admin_user):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = authenticated_api_client.patch(
            f"/api/v1/courses/{course.pk}/", {"title": "Updated"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Updated"

    def test_course_delete(self, authenticated_api_client, admin_user):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = authenticated_api_client.delete(f"/api/v1/courses/{course.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
@pytest.mark.django_db
class TestCoursesAPIPermissions:
    """A 'member' role user can read the course catalog but not write;
    'teacher'/'admin' can write."""

    def test_member_role_can_list_courses(
        self, regular_api_client_same_tenant, admin_user
    ):
        from education.models import Course

        Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = regular_api_client_same_tenant.get("/api/v1/courses/")
        assert response.status_code == status.HTTP_200_OK

    def test_member_role_cannot_create_course(self, regular_api_client_same_tenant):
        response = regular_api_client_same_tenant.post(
            "/api/v1/courses/", {"title": "Unauthorized Course"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_role_cannot_update_course(
        self, regular_api_client_same_tenant, admin_user
    ):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = regular_api_client_same_tenant.patch(
            f"/api/v1/courses/{course.pk}/", {"title": "Hacked"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_role_cannot_delete_course(
        self, regular_api_client_same_tenant, admin_user
    ):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Test Course")
        response = regular_api_client_same_tenant.delete(f"/api/v1/courses/{course.pk}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_role_can_still_create_course(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/v1/courses/", {"title": "Authorized Course"}
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.integration
@pytest.mark.django_db
class TestEnrollmentAPI:
    def test_enroll_blocked_returns_400_with_reason(
        self, authenticated_api_client, admin_user, member
    ):
        from education.models import Course

        course = Course.objects.create(
            tenant=admin_user.tenant, title="Baptism Required", requires_baptized=True
        )
        response = authenticated_api_client.post(
            "/api/v1/enrollments/", {"member": member.pk, "course": course.pk}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_enroll_succeeds_when_eligible(
        self, authenticated_api_client, admin_user, member
    ):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Open Course")
        response = authenticated_api_client.post(
            "/api/v1/enrollments/", {"member": member.pk, "course": course.pk}
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "enrolled"

    def test_duplicate_enrollment_rejected(
        self, authenticated_api_client, admin_user, member
    ):
        from education.models import Course

        course = Course.objects.create(tenant=admin_user.tenant, title="Open Course")
        authenticated_api_client.post(
            "/api/v1/enrollments/", {"member": member.pk, "course": course.pk}
        )
        response = authenticated_api_client.post(
            "/api/v1/enrollments/", {"member": member.pk, "course": course.pk}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
class TestEnrollmentAPIPermissions:
    """Enrolling/dropping follows CanManageMembers (admin/pastor/volunteer);
    marking an enrollment completed follows CanManageEducation (admin/teacher)."""

    def test_volunteer_role_can_enroll_member(
        self, api_client, user_factory, course_factory
    ):
        from members.models import Member

        volunteer = user_factory(email="volunteer@test.com", role="volunteer")
        api_client.force_authenticate(user=volunteer)
        course = course_factory()
        test_member = Member.objects.create(
            tenant=course.tenant, first_name="Enrollee", last_name="One"
        )

        response = api_client.post(
            "/api/v1/enrollments/", {"member": test_member.pk, "course": course.pk}
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_volunteer_role_cannot_mark_enrollment_complete(
        self, api_client, user_factory, course_factory
    ):
        from members.models import Member

        volunteer = user_factory(email="volunteer2@test.com", role="volunteer")
        api_client.force_authenticate(user=volunteer)
        course = course_factory()
        test_member = Member.objects.create(
            tenant=course.tenant, first_name="Enrollee", last_name="Two"
        )
        enroll_response = api_client.post(
            "/api/v1/enrollments/", {"member": test_member.pk, "course": course.pk}
        )
        enrollment_id = enroll_response.data["id"]

        response = api_client.patch(
            f"/api/v1/enrollments/{enrollment_id}/",
            {"status": "completed"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_role_can_mark_enrollment_complete(
        self, api_client, user_factory, course_factory
    ):
        from education.models import Enrollment
        from members.models import Member

        teacher = user_factory(email="teacher@test.com", role="teacher")
        api_client.force_authenticate(user=teacher)
        course = course_factory()
        test_member = Member.objects.create(
            tenant=course.tenant, first_name="Enrollee", last_name="Three"
        )

        enrollment = Enrollment.objects.create(
            tenant=course.tenant, member=test_member, course=course
        )

        response = api_client.patch(
            f"/api/v1/enrollments/{enrollment.pk}/",
            {"status": "completed"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        enrollment.refresh_from_db()
        assert enrollment.status == "completed"
