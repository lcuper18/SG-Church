"""
Managing a block's courses from the block page: add an existing standalone
course, take one out, and create a new course already assigned to the block.
"""

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from education.models import Course, CourseBlock, Enrollment
from members.models import Member, User
from tenants.models import Tenant


@pytest.fixture
def block(admin_user):
    return CourseBlock.objects.create(tenant=admin_user.tenant, name="Discipulado")


def _course(tenant, title, **kwargs):
    return Course.objects.create(tenant=tenant, title=title, **kwargs)


def _add(client, block, course):
    return client.post(reverse("block_add_course", args=[block.pk]), {"course": str(course.pk)})


@pytest.mark.django_db
class TestAddCourse:
    def test_adds_a_standalone_course_after_the_last_one(
        self, authenticated_client, admin_user, block
    ):
        tenant = admin_user.tenant
        _course(tenant, "Primero", course_block=block, order_in_block=1)
        loose = _course(tenant, "Suelto")

        response = _add(authenticated_client, block, loose)

        assert response.status_code == 302
        loose.refresh_from_db()
        assert loose.course_block == block and loose.order_in_block == 2

    def test_first_course_of_an_empty_block_gets_position_1(
        self, authenticated_client, admin_user, block
    ):
        loose = _course(admin_user.tenant, "Suelto")

        _add(authenticated_client, block, loose)

        loose.refresh_from_db()
        assert loose.order_in_block == 1

    def test_a_course_in_another_block_is_not_stolen(
        self, authenticated_client, admin_user, block
    ):
        other = CourseBlock.objects.create(tenant=admin_user.tenant, name="Otro")
        taken = _course(admin_user.tenant, "Ocupado", course_block=other)

        _add(authenticated_client, block, taken)

        taken.refresh_from_db()
        assert taken.course_block == other

    def test_other_churches_courses_and_blocks_are_off_limits(
        self, authenticated_client, admin_user, block
    ):
        foreign_tenant = Tenant.objects.create(name="Otra", subdomain="otra-blk")
        foreign_course = _course(foreign_tenant, "Ajeno")
        foreign_block = CourseBlock.objects.create(tenant=foreign_tenant, name="Bloque ajeno")
        mine = _course(admin_user.tenant, "Mío")

        _add(authenticated_client, block, foreign_course)
        foreign_course.refresh_from_db()
        assert foreign_course.course_block is None

        response = _add(authenticated_client, foreign_block, mine)
        assert response.status_code == 404
        mine.refresh_from_db()
        assert mine.course_block is None

    @pytest.mark.parametrize("value", ["", "not-a-uuid", str(uuid.uuid4())])
    def test_bad_course_value_is_handled(self, authenticated_client, block, value):
        response = authenticated_client.post(
            reverse("block_add_course", args=[block.pk]), {"course": value}
        )
        assert response.status_code == 302  # back to the block with an error message

    def test_get_is_not_allowed(self, authenticated_client, block):
        assert authenticated_client.get(
            reverse("block_add_course", args=[block.pk])
        ).status_code == 405

    @pytest.mark.parametrize("role", ["pastor", "treasurer", "volunteer", "member"])
    def test_only_admin_and_teacher_can_change_blocks(self, admin_user, block, role):
        loose = _course(admin_user.tenant, "Suelto")
        user = User.objects.create_user(
            email=f"{role}@t.com", password="x-Strong-pass-1", role=role, tenant=admin_user.tenant
        )
        client = Client()
        client.force_login(user)

        assert _add(client, block, loose).status_code == 403
        loose.refresh_from_db()
        assert loose.course_block is None

    def test_teacher_can(self, admin_user, block):
        loose = _course(admin_user.tenant, "Suelto")
        teacher = User.objects.create_user(
            email="t@t.com", password="x-Strong-pass-1", role="teacher", tenant=admin_user.tenant
        )
        client = Client()
        client.force_login(teacher)

        assert _add(client, block, loose).status_code == 302
        loose.refresh_from_db()
        assert loose.course_block == block


@pytest.mark.django_db
class TestRemoveCourse:
    def test_removes_it_and_leaves_it_standalone(self, authenticated_client, admin_user, block):
        course = _course(admin_user.tenant, "Uno", course_block=block, order_in_block=3)

        response = authenticated_client.post(
            reverse("block_remove_course", args=[block.pk, course.pk])
        )

        assert response.status_code == 302
        course.refresh_from_db()
        assert course.course_block is None and course.order_in_block == 0

    def test_cannot_remove_a_course_that_is_in_a_different_block(
        self, authenticated_client, admin_user, block
    ):
        other = CourseBlock.objects.create(tenant=admin_user.tenant, name="Otro")
        course = _course(admin_user.tenant, "Uno", course_block=other)

        response = authenticated_client.post(
            reverse("block_remove_course", args=[block.pk, course.pk])
        )

        assert response.status_code == 404
        course.refresh_from_db()
        assert course.course_block == other


@pytest.mark.django_db
class TestBlockPage:
    def test_offers_only_standalone_active_courses(self, authenticated_client, admin_user, block):
        tenant = admin_user.tenant
        free = _course(tenant, "Libre")
        _course(tenant, "Inactivo", is_active=False)
        _course(tenant, "En bloque", course_block=block)
        _course(Tenant.objects.create(name="O", subdomain="o-blk"), "Ajeno")

        response = authenticated_client.get(reverse("course_block_detail", args=[block.pk]))

        assert list(response.context["available_courses"]) == [free]
        html = response.content.decode()
        assert reverse("block_add_course", args=[block.pk]) in html
        assert f'{reverse("course_create")}?block={block.pk}' in html

    def test_read_only_users_see_no_controls(self, admin_user, block):
        _course(admin_user.tenant, "Libre")
        viewer = User.objects.create_user(
            email="v@t.com", password="x-Strong-pass-1", role="member", tenant=admin_user.tenant
        )
        client = Client()
        client.force_login(viewer)

        html = client.get(reverse("course_block_detail", args=[block.pk])).content.decode()

        assert reverse("block_add_course", args=[block.pk]) not in html

    def test_a_course_added_later_counts_for_the_certificate(self, admin_user, block):
        tenant = admin_user.tenant
        first = _course(tenant, "Uno", course_block=block)
        member = Member.objects.create(tenant=tenant, first_name="Ana", last_name="Mora")
        enrollment = Enrollment.objects.create(tenant=tenant, member=member, course=first)
        enrollment.mark_completed()
        assert block.certificates.count() == 1

        second = _course(tenant, "Dos")  # joins the block after Ana finished
        second.course_block = block
        second.save()
        enrollment2 = Enrollment.objects.create(tenant=tenant, member=member, course=second)
        enrollment2.mark_completed()

        assert block.certificates.filter(member=member).count() == 1  # never duplicated


@pytest.mark.django_db
class TestCreateCourseInBlock:
    def test_form_is_prefilled_with_the_block_and_next_position(
        self, authenticated_client, admin_user, block
    ):
        _course(admin_user.tenant, "Uno", course_block=block, order_in_block=4)

        response = authenticated_client.get(reverse("course_create"), {"block": str(block.pk)})

        form = response.context["form"]
        assert str(form["course_block"].value()) == str(block.pk)
        assert form["order_in_block"].value() == 5

    def test_after_saving_it_returns_to_the_block(self, authenticated_client, admin_user, block):
        response = authenticated_client.post(
            f'{reverse("course_create")}?block={block.pk}',
            {"title": "Nuevo", "course_block": str(block.pk), "order_in_block": 1, "is_active": "on"},
        )

        assert response.status_code == 302
        assert response.url == reverse("course_block_detail", args=[block.pk])
        assert Course.objects.get(title="Nuevo").course_block == block

    def test_a_foreign_or_bogus_block_param_is_ignored(self, authenticated_client):
        foreign = CourseBlock.objects.create(
            tenant=Tenant.objects.create(name="O", subdomain="o-blk2"), name="Ajeno"
        )

        for value in (str(foreign.pk), "not-a-uuid"):
            response = authenticated_client.get(reverse("course_create"), {"block": value})
            assert response.status_code == 200
            assert not response.context["form"]["course_block"].value()
