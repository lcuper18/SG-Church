"""
Audit trail ("bitácora") and trash ("papelera"): deleting is reversible, every
change is attributed, and both are for church administrators only.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from education.models import BlockCertificate, Course, CourseBlock, Enrollment
from events.models import Event, EventRegistration
from finance.models import Donation, Expense
from members.models import Family, Member, User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"


def login_as(role, tenant, **kwargs):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role,
        tenant=tenant, **kwargs,
    )
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def ana(tenant):
    return Member.objects.create(tenant=tenant, first_name="Ana", last_name="Mora", phone="111")


def entries(**filters):
    return list(AuditLog.objects.filter(**filters).order_by("created_at"))


@pytest.mark.django_db
class TestAuditTrail:
    def test_web_edits_are_attributed_to_the_user_with_a_field_diff(
        self, authenticated_client, admin_user, ana
    ):
        authenticated_client.post(
            reverse("member_update", args=[ana.pk]),
            {"first_name": "Ana", "last_name": "Mora", "phone": "222", "member_status": "member"},
        )

        update = entries(action="update", object_id=str(ana.pk))[-1]

        assert update.user == admin_user and update.user_label == admin_user.email
        assert update.model_label == "members.member" and update.object_repr == "Ana Mora"
        assert update.changes["phone"] == ["111", "222"]
        assert "first_name" not in update.changes  # unchanged fields aren't listed

    def test_creation_through_the_api_is_logged_too(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.post(
            "/api/v1/members/", {"first_name": "Beto", "last_name": "Solís"}, format="json"
        )
        assert response.status_code == 201

        created = entries(action="create", model_label="members.member")[-1]
        assert created.user == admin_user and created.object_repr == "Beto Solís"

    def test_work_outside_a_request_is_attributed_to_the_system(self, tenant):
        Member.objects.create(tenant=tenant, first_name="Seed", last_name="Dato")
        assert entries(model_label="members.member")[-1].user_label == "Sistema"

    def test_saves_that_change_nothing_leave_no_entry(self, tenant, ana):
        before = AuditLog.objects.count()
        ana.save()
        assert AuditLog.objects.count() == before

    def test_pastoral_notes_and_passwords_are_logged_as_changed_but_never_shown(
        self, tenant, ana, admin_user
    ):
        ana.notes = "algo muy privado"
        ana.save()
        admin_user.set_password("otra-clave-9921")
        admin_user.save()

        assert entries(object_id=str(ana.pk), action="update")[-1].changes == {"notes": ["•••", "•••"]}
        assert entries(object_id=str(admin_user.pk), action="update")[-1].changes == {
            "password": ["•••", "•••"]
        }
        logged = " ".join(str(e.changes) for e in AuditLog.objects.all())
        assert "muy privado" not in logged and "otra-clave" not in logged

    def test_role_changes_are_recorded(self, tenant):
        _, target = login_as("volunteer", tenant)
        target.role = "treasurer"
        target.save()
        assert entries(object_id=str(target.pk), action="update")[-1].changes["role"] == [
            "volunteer", "treasurer",
        ]

    def test_money_and_course_records_are_covered(self, tenant, ana):
        donation = Donation.objects.create(tenant=tenant, amount=Decimal("10.00"), status="pending")
        donation.status = "completed"
        donation.save()
        assert entries(model_label="finance.donation", action="update")[-1].changes["status"] == [
            "pending", "completed",
        ]

    def test_an_audit_failure_never_blocks_the_action(self, tenant, monkeypatch):
        from core import audit

        monkeypatch.setattr(
            "core.models.AuditLog.objects.create", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        member = Member.objects.create(tenant=tenant, first_name="Sigue", last_name="Igual")
        assert Member.objects.filter(pk=member.pk).exists()
        assert audit  # imported only to document what is being exercised


@pytest.mark.django_db
class TestSoftDelete:
    def test_deleting_hides_the_record_everywhere_but_keeps_the_row(
        self, authenticated_client, tenant, ana
    ):
        response = authenticated_client.post(reverse("member_delete", args=[ana.pk]))

        assert response.status_code == 302
        assert not Member.objects.filter(pk=ana.pk).exists()
        trashed = Member.all_objects.get(pk=ana.pk)
        assert trashed.is_deleted and trashed.deleted_by is not None
        assert authenticated_client.get(reverse("member_detail", args=[ana.pk])).status_code == 404
        listed = authenticated_client.get(reverse("member_list")).context["members"]
        assert ana not in list(listed)
        assert authenticated_client.get(reverse("member_lookup"), {"q": "ana"}).json()["total"] == 0

    def test_api_delete_goes_to_the_trash_too(self, authenticated_api_client, ana):
        assert authenticated_api_client.delete(f"/api/v1/members/{ana.pk}/").status_code == 204
        assert Member.all_objects.get(pk=ana.pk).is_deleted

    def test_a_trashed_person_takes_their_enrollments_and_registrations_with_them(self, tenant, ana):
        block = CourseBlock.objects.create(tenant=tenant, name="Discipulado")
        course = Course.objects.create(tenant=tenant, title="Fundamentos", course_block=block)
        Enrollment.objects.create(tenant=tenant, member=ana, course=course).mark_completed()
        event = Event.objects.create(
            tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=2)
        )
        EventRegistration.objects.create(tenant=tenant, member=ana, event=event)
        assert event.registered_count == 1 and BlockCertificate.objects.count() == 1

        ana.delete()

        assert course.enrollments.count() == 0
        assert event.registered_count == 0 and BlockCertificate.objects.count() == 0

        ana.restore()

        assert course.enrollments.count() == 1
        assert event.registered_count == 1 and BlockCertificate.objects.count() == 1

    def test_donations_survive_the_donors_deletion(self, tenant, ana):
        donation = Donation.objects.create(
            tenant=tenant, member=ana, amount=Decimal("50.00"), status="completed"
        )
        ana.delete()
        donation.refresh_from_db()
        assert donation.member_id == ana.pk and donation.member.full_name == "Ana Mora"

    def test_trashing_a_head_of_family_clears_the_headship(self, tenant, ana):
        family = Family.objects.create(tenant=tenant, name="Mora", head_of_family=ana)
        ana.family = family
        ana.save()

        ana.delete()

        family.refresh_from_db()
        assert family.head_of_family is None

    def test_a_family_name_can_be_reused_while_the_old_one_is_in_the_trash(self, tenant):
        old = Family.objects.create(tenant=tenant, name="Rojas")
        old.delete()

        Family.objects.create(tenant=tenant, name="Rojas")  # no IntegrityError

        assert Family.all_objects.filter(tenant=tenant, name="Rojas").count() == 2

    def test_trashing_a_block_frees_its_courses(self, tenant):
        block = CourseBlock.objects.create(tenant=tenant, name="Bloque")
        course = Course.objects.create(tenant=tenant, title="Curso", course_block=block)
        block.delete()
        course.refresh_from_db()
        assert course.course_block is None

    def test_trashed_expenses_leave_the_totals(self, authenticated_client, tenant):
        expense = Expense.objects.create(
            tenant=tenant, description="Luz", amount=Decimal("40.00"), expense_date=timezone.localdate()
        )
        tenant.onboarding_completed = True
        tenant.save()
        shown = authenticated_client.get(reverse("finance_dashboard")).context["expenses_this_month"]
        assert shown == Decimal("40.00")

        expense.delete()

        assert authenticated_client.get(reverse("finance_dashboard")).context["expenses_this_month"] == 0

    def test_deleting_and_restoring_are_audited(self, tenant, ana):
        ana.delete()
        ana.restore()
        assert [e.action for e in entries(object_id=str(ana.pk))][-2:] == ["delete", "restore"]

    def test_a_linked_login_stops_seeing_a_trashed_record(self, tenant, ana):
        client, _ = login_as("member", tenant, member_profile=ana)
        ana.delete()
        assert "aún no está vinculado" in client.get(reverse("my_record")).content.decode()


@pytest.mark.django_db
class TestTrashScreen:
    def test_only_church_admins_can_open_the_trash_and_the_audit(self, tenant):
        for role in ("pastor", "treasurer", "teacher", "volunteer", "member"):
            client, _ = login_as(role, tenant)
            assert client.get(reverse("trash")).status_code == 403, role
            assert client.get(reverse("audit_log")).status_code == 403, role
        assert Client().get(reverse("trash")).status_code == 302

    def test_lists_restores_and_purges(self, authenticated_client, tenant, ana):
        ana.delete()
        page = authenticated_client.get(reverse("trash")).content.decode()
        assert "Ana Mora" in page and "Miembro" in page

        response = authenticated_client.post(reverse("trash_restore", args=["members.member", ana.pk]))
        assert response.status_code == 302
        assert Member.objects.filter(pk=ana.pk).exists()

        ana.delete()
        authenticated_client.post(reverse("trash_purge", args=["members.member", ana.pk]))
        assert not Member.all_objects.filter(pk=ana.pk).exists()
        assert entries(object_id=str(ana.pk))[-1].action == "purge"

    def test_other_churches_trash_is_untouchable(self, authenticated_client):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        foreign = Member.objects.create(tenant=other, first_name="Ajena", last_name="X")
        foreign.delete()

        assert "Ajena" not in authenticated_client.get(reverse("trash")).content.decode()
        response = authenticated_client.post(
            reverse("trash_restore", args=["members.member", foreign.pk])
        )
        assert response.status_code == 404
        assert Member.all_objects.get(pk=foreign.pk).is_deleted

    def test_unknown_types_are_rejected(self, authenticated_client, ana):
        response = authenticated_client.post(reverse("trash_restore", args=["auth.group", ana.pk]))
        assert response.status_code == 404

    def test_restoring_over_a_taken_name_explains_instead_of_crashing(
        self, authenticated_client, tenant
    ):
        old = Family.objects.create(tenant=tenant, name="Rojas")
        old.delete()
        Family.objects.create(tenant=tenant, name="Rojas")

        response = authenticated_client.post(
            reverse("trash_restore", args=["members.family", old.pk]), follow=True
        )

        assert "ya existe otro registro" in response.content.decode()
        assert Family.all_objects.get(pk=old.pk).is_deleted

    def test_the_nightly_purge_removes_only_what_is_old_enough(self, tenant, settings):
        from core.tasks import purge_trash

        settings.TRASH_RETENTION_DAYS = 30
        old = Member.objects.create(tenant=tenant, first_name="Vieja", last_name="Papelera")
        recent = Member.objects.create(tenant=tenant, first_name="Reciente", last_name="Papelera")
        old.delete()
        recent.delete()
        Member.all_objects.filter(pk=old.pk).update(deleted_at=timezone.now() - timedelta(days=31))

        assert purge_trash() == 1

        assert not Member.all_objects.filter(pk=old.pk).exists()
        assert Member.all_objects.filter(pk=recent.pk).exists()

    def test_deleting_a_whole_church_still_works(self, tenant, ana):
        """Auditing must not get in the way of removing a tenant."""
        Family.objects.create(tenant=tenant, name="Mora")
        tenant.delete()
        assert not Member.all_objects.filter(pk=ana.pk).exists()


@pytest.mark.django_db
class TestAuditScreen:
    def test_shows_and_filters_entries(self, authenticated_client, tenant, ana):
        ana.last_name = "Núñez"
        ana.save()
        Family.objects.create(tenant=tenant, name="Rojas")

        page = authenticated_client.get(reverse("audit_log")).content.decode()
        assert "Núñez" in page and "Apellido" in page and "Mora" in page

        only_members = authenticated_client.get(reverse("audit_log"), {"model": "members.member"})
        assert all(e.model_label == "members.member" for e in only_members.context["entries"])
        only_updates = authenticated_client.get(reverse("audit_log"), {"action": "update"})
        assert all(e.action == "update" for e in only_updates.context["entries"])
        search = authenticated_client.get(reverse("audit_log"), {"q": "rojas"})
        assert [e.object_repr for e in search.context["entries"]] == ["Rojas"]

    def test_only_this_churchs_entries(self, authenticated_client, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        Member.objects.create(tenant=other, first_name="Ajena", last_name="Secreta")

        assert "Secreta" not in authenticated_client.get(reverse("audit_log")).content.decode()
