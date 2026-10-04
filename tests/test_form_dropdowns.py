"""
Regression tests: the hand-written forms must list the tenant's related
objects in their <select> dropdowns and preselect the saved one on edit.

`form.<field>.queryset` renders nothing in a Django template (a BoundField has
no queryset); it has to be `form.fields.<field>.queryset`. These tests render
the real pages, since posting form data directly never exercises that.
"""

import re

import pytest

from education.models import Course, CourseBlock
from events.models import Event
from members.models import Family, Member


def _select(html, field_id):
    match = re.search(rf'<select[^>]*id="{field_id}".*?</select>', html, re.S)
    assert match, f"no <select id={field_id}> found"
    return match.group(0)


def _option(select_html, value):
    match = re.search(rf'<option value="{value}"([^>]*)>', select_html)
    assert match, f"option {value} not listed"
    return match.group(1)


@pytest.mark.django_db
class TestFormDropdowns:
    def test_member_form_lists_families_and_preselects_on_edit(
        self, authenticated_client, admin_user
    ):
        family = Family.objects.create(tenant=admin_user.tenant, name="Familia Mora")
        member = Member.objects.create(
            tenant=admin_user.tenant, first_name="A", last_name="B", family=family
        )

        new_page = authenticated_client.get("/members/create/").content.decode()
        assert str(family.pk) in _select(new_page, "family")

        edit_page = authenticated_client.get(f"/members/{member.pk}/edit/").content.decode()
        assert "selected" in _option(_select(edit_page, "family"), family.pk)

    def test_family_form_lists_members_and_preselects_head(
        self, authenticated_client, admin_user
    ):
        head = Member.objects.create(tenant=admin_user.tenant, first_name="H", last_name="X")
        family = Family.objects.create(
            tenant=admin_user.tenant, name="Familia X", head_of_family=head
        )

        page = authenticated_client.get(f"/members/families/{family.pk}/edit/").content.decode()

        assert "selected" in _option(_select(page, "head_of_family"), head.pk)

    def test_course_form_lists_and_preselects_block_instructor_prerequisites(
        self, authenticated_client, admin_user
    ):
        block = CourseBlock.objects.create(tenant=admin_user.tenant, name="Bloque")
        prereq = Course.objects.create(tenant=admin_user.tenant, title="Base")
        course = Course.objects.create(
            tenant=admin_user.tenant,
            title="Avanzado",
            course_block=block,
            instructor=admin_user,
        )
        course.prerequisite_courses.add(prereq)

        new_page = authenticated_client.get("/education/create/").content.decode()
        assert str(block.pk) in _select(new_page, "course_block")
        assert str(admin_user.pk) in _select(new_page, "instructor")
        assert str(prereq.pk) in _select(new_page, "prerequisite_courses")

        edit_page = authenticated_client.get(f"/education/{course.pk}/edit/").content.decode()
        assert "selected" in _option(_select(edit_page, "course_block"), block.pk)
        assert "selected" in _option(_select(edit_page, "instructor"), admin_user.pk)
        assert "selected" in _option(_select(edit_page, "prerequisite_courses"), prereq.pk)

    def test_event_form_lists_and_preselects_required_courses(
        self, authenticated_client, admin_user
    ):
        from django.utils import timezone

        course = Course.objects.create(tenant=admin_user.tenant, title="Liderazgo")
        event = Event.objects.create(
            tenant=admin_user.tenant, title="Cumbre", start_at=timezone.now()
        )
        event.required_courses.add(course)

        new_page = authenticated_client.get("/events/create/").content.decode()
        assert str(course.pk) in _select(new_page, "required_courses")

        edit_page = authenticated_client.get(f"/events/{event.pk}/edit/").content.decode()
        assert "selected" in _option(_select(edit_page, "required_courses"), course.pk)

    def test_dropdowns_only_list_own_tenant(self, authenticated_client, tenant):
        foreign = Course.objects.create(tenant=tenant, title="De otra iglesia")

        page = authenticated_client.get("/events/create/").content.decode()

        assert str(foreign.pk) not in _select(page, "required_courses")
