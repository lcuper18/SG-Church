"""
Pastoral follow-up: who can see it, recording / completing / editing, the
suggestions (new visitors, people who stopped coming) and the audit trail.
"""

import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from events.models import Event, EventAttendance
from members.followups import suggestions
from members.models import FollowUp, Member, User

STRONG = "Str0ng-Passw0rd!x"
SECRET = "Lucha con una pérdida familiar"


def login_as(role, tenant):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role, tenant=tenant,
        first_name=role.capitalize(), last_name="Prueba",
    )
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def pastor(tenant):
    return login_as("pastor", tenant)


@pytest.fixture
def ana(tenant):
    return Member.objects.create(tenant=tenant, first_name="Ana", last_name="Pérez", member_status="member")


def add(client, member, **data):
    payload = {"kind": "call", "notes": SECRET, "due_date": "2030-01-10"}
    payload.update(data)
    return client.post(reverse("follow_up_add", args=[member.pk]), payload)


@pytest.mark.django_db
class TestWhoSees:
    def test_pastors_and_admins_yes(self, tenant, pastor, authenticated_client, ana):
        for client in (pastor[0], authenticated_client):
            assert client.get(reverse("follow_up_list")).status_code == 200

    @pytest.mark.parametrize("role", ["volunteer", "treasurer", "teacher", "member"])
    def test_other_roles_no(self, tenant, ana, role):
        client, _ = login_as(role, tenant)
        assert client.get(reverse("follow_up_list")).status_code == 403
        assert add(client, ana).status_code == 403
        assert FollowUp.objects.count() == 0

    def test_a_volunteer_does_not_see_the_tab_or_notes(self, tenant, pastor, ana):
        add(pastor[0], ana)
        volunteer, _ = login_as("volunteer", tenant)
        html = volunteer.get(reverse("member_detail", args=[ana.pk])).content.decode()
        assert "followups-tab" not in html and SECRET not in html

    def test_pastor_sees_it_on_the_member_page(self, pastor, ana):
        add(pastor[0], ana)
        html = pastor[0].get(reverse("member_detail", args=[ana.pk])).content.decode()
        assert "followups-tab" in html and SECRET in html

    def test_another_church_cannot_touch_it(self, pastor, ana):
        from tenants.models import Tenant

        other = Tenant.objects.create(name="Otra", subdomain="otra-fu")
        client, _ = login_as("pastor", other)
        add(pastor[0], ana)
        item = FollowUp.objects.get()
        assert add(client, ana).status_code == 404
        assert client.post(reverse("follow_up_done", args=[item.pk])).status_code == 404
        assert client.get(reverse("follow_up_edit", args=[item.pk])).status_code == 404

    def test_not_in_the_api(self, pastor, ana):
        add(pastor[0], ana)
        assert SECRET not in pastor[0].get("/api/v1/members/").content.decode()


@pytest.mark.django_db
class TestLifecycle:
    def test_add_defaults_to_the_author_and_open(self, pastor, ana):
        add(pastor[0], ana)
        item = FollowUp.objects.get()
        assert (item.status, item.assigned_to, item.created_by) == ("open", pastor[1], pastor[1])

    def test_add_as_already_done(self, pastor, ana):
        add(pastor[0], ana, done="on")
        item = FollowUp.objects.get()
        assert item.status == "done" and item.completed_at is not None

    def test_assign_to_another_pastor_only_from_this_church(self, tenant, pastor, ana, authenticated_client, admin_user):
        add(pastor[0], ana, assigned_to=str(admin_user.pk))
        assert FollowUp.objects.get().assigned_to == admin_user
        FollowUp.objects.all().delete()
        from tenants.models import Tenant

        stranger = User.objects.create_user(
            email="x@x.com", password=STRONG, role="pastor", tenant=Tenant.objects.create(name="Z", subdomain="zz-fu")
        )
        add(pastor[0], ana, assigned_to=str(stranger.pk))
        assert FollowUp.objects.count() == 0  # the form refuses a user of another church

    def test_done_reopen_and_plan_the_next(self, pastor, ana):
        add(pastor[0], ana)
        item = FollowUp.objects.get()
        pastor[0].post(reverse("follow_up_done", args=[item.pk]), {"next_due": "2030-02-01"})
        item.refresh_from_db()
        assert item.status == "done"
        nxt = FollowUp.objects.get(status="open")
        assert str(nxt.due_date) == "2030-02-01" and nxt.member == ana
        pastor[0].post(reverse("follow_up_reopen", args=[item.pk]))
        item.refresh_from_db()
        assert item.status == "open" and item.completed_at is None

    def test_a_bad_next_date_is_ignored(self, pastor, ana):
        add(pastor[0], ana)
        item = FollowUp.objects.get()
        pastor[0].post(reverse("follow_up_done", args=[item.pk]), {"next_due": "mañana"})
        assert FollowUp.objects.count() == 1

    def test_edit_and_delete(self, pastor, ana):
        add(pastor[0], ana)
        item = FollowUp.objects.get()
        pastor[0].post(reverse("follow_up_edit", args=[item.pk]), {"kind": "visit", "notes": "Nuevo", "done": "on"})
        item.refresh_from_db()
        assert (item.kind, item.notes, item.status) == ("visit", "Nuevo", "done")
        pastor[0].post(reverse("follow_up_delete", args=[item.pk]))
        assert FollowUp.objects.count() == 0

    def test_a_trashed_member_hides_their_follow_up(self, pastor, ana):
        add(pastor[0], ana)
        ana.soft_delete()
        assert FollowUp.objects.count() == 0


@pytest.mark.django_db
class TestList:
    def test_mine_overdue_and_filters(self, tenant, pastor, ana, admin_user):
        today = timezone.localdate()
        FollowUp.objects.create(tenant=tenant, member=ana, due_date=today - timedelta(days=3), assigned_to=pastor[1])
        FollowUp.objects.create(tenant=tenant, member=ana, kind="visit", due_date=today + timedelta(days=3), assigned_to=admin_user)
        html = pastor[0].get(reverse("follow_up_list")).content.decode()
        assert "Vencido" in html and "Visita" not in html  # mine only by default
        everyone = pastor[0].get(reverse("follow_up_list"), {"who": "all"}).content.decode()
        assert "Visita" in everyone

    def test_counts(self, tenant, pastor, ana):
        FollowUp.objects.create(tenant=tenant, member=ana, due_date=timezone.localdate() - timedelta(days=1), assigned_to=pastor[1])
        context = pastor[0].get(reverse("follow_up_list")).context
        assert context["counts"] == {"mine": 1, "overdue": 1, "total": 1}


@pytest.mark.django_db
class TestSuggestions:
    def held(self, tenant, days_ago, *members):
        event = Event.objects.create(tenant=tenant, title="Culto", start_at=timezone.now() - timedelta(days=days_ago))
        for member in members:
            EventAttendance.objects.create(tenant=tenant, member=member, event=event)
        return event

    def test_new_visitors_without_contact(self, tenant, pastor):
        new = Member.objects.create(tenant=tenant, first_name="Nuevo", last_name="V", member_status="visitor")
        contacted = Member.objects.create(tenant=tenant, first_name="Ya", last_name="V", member_status="visitor")
        FollowUp.objects.create(tenant=tenant, member=contacted)
        old = Member.objects.create(tenant=tenant, first_name="Viejo", last_name="V", member_status="visitor")
        Member.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=90))
        visitors, _ = suggestions(tenant)
        assert visitors == [new]

    def test_people_who_stopped_coming(self, tenant):
        gone = Member.objects.create(tenant=tenant, first_name="Ausente", last_name="A", member_status="member")
        regular = Member.objects.create(tenant=tenant, first_name="Fiel", last_name="F", member_status="member")
        never = Member.objects.create(tenant=tenant, first_name="Nunca", last_name="N", member_status="member")
        inactive = Member.objects.create(tenant=tenant, first_name="Baja", last_name="B", member_status="inactive")
        self.held(tenant, 80, gone, regular, inactive)
        self.held(tenant, 7, regular)
        _, away = suggestions(tenant)
        assert away == [gone] and never not in away

    def test_nobody_is_absent_if_no_attendance_was_taken_lately(self, tenant):
        gone = Member.objects.create(tenant=tenant, first_name="Ausente", last_name="A", member_status="member")
        self.held(tenant, 80, gone)
        assert suggestions(tenant)[1] == []

    def test_a_recent_follow_up_silences_the_suggestion(self, tenant):
        gone = Member.objects.create(tenant=tenant, first_name="Ausente", last_name="A", member_status="member")
        other = Member.objects.create(tenant=tenant, first_name="Otro", last_name="O", member_status="member")
        self.held(tenant, 80, gone)
        self.held(tenant, 7, other)
        FollowUp.objects.create(tenant=tenant, member=gone)
        assert suggestions(tenant)[1] == []

    def test_one_click_from_the_page(self, tenant, pastor):
        person = Member.objects.create(tenant=tenant, first_name="Nuevo", last_name="V", member_status="visitor")
        html = pastor[0].get(reverse("follow_up_list")).content.decode()
        assert "Nuevo V" in html and "Dar seguimiento" in html
        response = pastor[0].post(
            reverse("follow_up_add", args=[person.pk]), {"back": "list", "kind": "call", "due_date": "2030-01-01"}
        )
        assert response.status_code == 302 and response.url == reverse("follow_up_list")
        assert FollowUp.objects.get().member == person


@pytest.mark.django_db
class TestAudit:
    def test_changes_are_logged_but_notes_are_masked(self, pastor, ana):
        add(pastor[0], ana)
        entries = AuditLog.objects.filter(model_label="members.followup")
        assert entries.exists()
        assert SECRET not in str([e.changes for e in entries])
        item = FollowUp.objects.get()
        pastor[0].post(reverse("follow_up_edit", args=[item.pk]), {"kind": "call", "notes": "Otra cosa"})
        assert "Otra cosa" not in str([e.changes for e in AuditLog.objects.filter(model_label="members.followup")])
