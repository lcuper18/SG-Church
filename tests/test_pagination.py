"""
Long lists are paged: courses, course blocks, church users, and the enrolled / registered /
progress tables on the detail pages. Counts stay about everyone, not just the page on screen.
"""

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from core.pagination import paginate
from education.models import Course, CourseBlock, Enrollment
from events.models import Event, EventRegistration
from members.models import Member, User


@pytest.fixture
def tenant(admin_user):
    admin_user.tenant.onboarding_completed = True
    admin_user.tenant.save()
    return admin_user.tenant


def people(tenant, count):
    Member.objects.bulk_create(
        [Member(tenant=tenant, first_name=f"Nombre{index:03d}", last_name=f"Apellido{index:03d}") for index in range(count)]
    )
    return list(Member.objects.filter(tenant=tenant).order_by("last_name"))


@pytest.mark.django_db
class TestHelper:
    def test_bad_pages_never_raise(self, rf):
        items = list(range(120))
        assert paginate(rf.get("/?page=2"), items).number == 2
        assert paginate(rf.get("/?page=abc"), items).number == 1
        assert paginate(rf.get("/?page=99"), items).number == 3
        assert len(paginate(rf.get("/"), items).object_list) == 50


@pytest.mark.django_db
class TestLists:
    def test_courses(self, authenticated_client, tenant):
        Course.objects.bulk_create([Course(tenant=tenant, title=f"Curso {i:02d}") for i in range(30)])
        first = authenticated_client.get(reverse("course_list"))
        assert len(first.context["courses"]) == 25 and "Página 1 de 2" in first.content.decode()
        assert len(authenticated_client.get(reverse("course_list"), {"page": 2}).context["courses"]) == 5

    def test_blocks(self, authenticated_client, tenant):
        CourseBlock.objects.bulk_create([CourseBlock(tenant=tenant, name=f"Bloque {i:02d}") for i in range(30)])
        assert len(authenticated_client.get(reverse("course_block_list")).context["course_blocks"]) == 25

    def test_users(self, authenticated_client, tenant):
        for index in range(55):
            User.objects.create_user(email=f"u{index}-{uuid.uuid4().hex[:4]}@t.com", password="Clave-Segura-2026", role="member", tenant=tenant)
        page = authenticated_client.get(reverse("user_list"))
        assert len(page.context["church_users"]) == 50 and "Página 1 de 2" in page.content.decode()


@pytest.mark.django_db
class TestDetailTables:
    def test_course_enrollments(self, authenticated_client, tenant):
        course = Course.objects.create(tenant=tenant, title="Discipulado")
        for member in people(tenant, 60):
            Enrollment.objects.create(tenant=tenant, member=member, course=course)
        response = authenticated_client.get(reverse("course_detail", args=[course.pk]))
        assert len(response.context["enrollments"]) == 50
        html = response.content.decode()
        assert "Nombre000" in html and "Nombre059" not in html and "Página 1 de 2" in html
        second = authenticated_client.get(reverse("course_detail", args=[course.pk]), {"page": 2})
        assert "Nombre059" in second.content.decode()

    def test_event_registrations_page_but_counts_are_for_everyone(self, authenticated_client, tenant):
        event = Event.objects.create(tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=3))
        for member in people(tenant, 60):
            EventRegistration.objects.create(tenant=tenant, member=member, event=event)
        response = authenticated_client.get(reverse("event_detail", args=[event.pk]))
        assert len(response.context["registrations"]) == 50
        assert response.context["no_show_count"] == 60  # not 50
        assert event.registered_count == 60

    def test_block_progress(self, authenticated_client, tenant):
        block = CourseBlock.objects.create(tenant=tenant, name="Fundamentos")
        course = Course.objects.create(tenant=tenant, title="Uno", course_block=block)
        for member in people(tenant, 60):
            Enrollment.objects.create(tenant=tenant, member=member, course=course)
        response = authenticated_client.get(reverse("course_block_detail", args=[block.pk]))
        assert len(response.context["progress"]) == 50 and response.context["page_obj"].paginator.count == 60
