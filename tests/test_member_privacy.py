"""
Who may see the members' personal data.

The directory (phones, addresses, birth dates), the pastoral notes and each
person's giving used to be readable by any logged-in user, a plain "member"
included. These tests pin down the narrower rules:

- directory (list/detail, families, tags): admin, pastor, volunteer
- pastoral notes: admin, pastor
- giving on a member's page: admin, treasurer
- who is enrolled/registered: member managers (+ teachers for courses)
- everyone: their own record at /me/
"""

import re
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from education.models import BlockCertificate, Course, CourseBlock, Enrollment
from events.models import Event, EventRegistration
from finance.models import Donation
from members.models import Family, Member, User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"
NOTE = "Nota pastoral muy privada"
AMOUNT = Decimal("7777.00")


def shows(page, digits_before, digits_after):
    """The localized money text (e.g. '$7 777,00', with a no-break space)."""
    return re.search(rf"{digits_before}\s{digits_after},00", page) is not None


def login_as(role, tenant, **kwargs):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com",
        password=STRONG,
        role=role,
        tenant=tenant,
        **kwargs,
    )
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def person(tenant):
    member = Member.objects.create(
        tenant=tenant, first_name="Marta", last_name="Vargas", notes=NOTE,
        phone="555-0100", is_baptized=True,
    )
    Donation.objects.create(tenant=tenant, member=member, amount=AMOUNT, status="completed")
    return member


@pytest.fixture
def family(tenant, person):
    family = Family.objects.create(tenant=tenant, name="Vargas", notes="Nota de familia privada")
    person.family = family
    person.save()
    return family


@pytest.mark.django_db
class TestDirectoryAccess:
    URLS = ["member_list", "family_list", "tag_list"]

    @pytest.mark.parametrize("role", ["member", "treasurer", "teacher"])
    def test_roles_without_member_management_get_403(self, role, tenant, person, family):
        client, _ = login_as(role, tenant)
        for name in self.URLS:
            assert client.get(reverse(name)).status_code == 403, name
        assert client.get(reverse("member_detail", args=[person.pk])).status_code == 403
        assert client.get(reverse("family_detail", args=[family.pk])).status_code == 403
        assert client.get(reverse("member_export")).status_code == 403

    @pytest.mark.parametrize("role", ["admin", "pastor", "volunteer"])
    def test_member_managers_can_open_them(self, role, tenant, person, family):
        client, _ = login_as(role, tenant)
        for name in self.URLS:
            assert client.get(reverse(name)).status_code == 200, name
        assert client.get(reverse("member_detail", args=[person.pk])).status_code == 200
        assert client.get(reverse("family_detail", args=[family.pk])).status_code == 200

    def test_anonymous_is_sent_to_login(self, person):
        response = Client().get(reverse("member_detail", args=[person.pk]))
        assert response.status_code == 302 and "login" in response.url


@pytest.mark.django_db
class TestPastoralNotesAndGiving:
    def test_pastor_sees_the_notes_but_not_the_giving(self, tenant, person):
        client, _ = login_as("pastor", tenant)
        page = client.get(reverse("member_detail", args=[person.pk])).content.decode()
        assert NOTE in page
        assert not shows(page, 7, 777) and 'id="donations"' not in page

    def test_volunteer_sees_neither_notes_nor_giving(self, tenant, person):
        client, _ = login_as("volunteer", tenant)
        page = client.get(reverse("member_detail", args=[person.pk])).content.decode()
        assert NOTE not in page
        assert not shows(page, 7, 777) and 'id="donations"' not in page

    def test_admin_sees_both(self, tenant, person):
        client, _ = login_as("admin", tenant)
        page = client.get(reverse("member_detail", args=[person.pk])).content.decode()
        assert NOTE in page and 'id="donations"' in page
        assert shows(page, 7, 777)

    def test_family_notes_follow_the_same_rule(self, tenant, family):
        volunteer, _ = login_as("volunteer", tenant)
        pastor, _ = login_as("pastor", tenant)
        url = reverse("family_detail", args=[family.pk])
        assert "Nota de familia privada" not in volunteer.get(url).content.decode()
        assert "Nota de familia privada" in pastor.get(url).content.decode()

    def test_volunteer_form_has_no_notes_field_and_cannot_overwrite_them(self, tenant, person):
        client, _ = login_as("volunteer", tenant)
        url = reverse("member_update", args=[person.pk])
        assert 'name="notes"' not in client.get(url).content.decode()

        response = client.post(
            url,
            {"first_name": "Marta", "last_name": "Vargas", "member_status": "member",
             "notes": "sobrescrita"},
        )

        assert response.status_code == 302
        person.refresh_from_db()
        assert person.notes == NOTE

    def test_pastor_can_edit_the_notes(self, tenant, person):
        client, _ = login_as("pastor", tenant)
        url = reverse("member_update", args=[person.pk])
        assert 'name="notes"' in client.get(url).content.decode()

        client.post(
            url,
            {"first_name": "Marta", "last_name": "Vargas", "member_status": "member",
             "notes": "nueva nota"},
        )

        person.refresh_from_db()
        assert person.notes == "nueva nota"


@pytest.mark.django_db
class TestApi:
    def _client(self, role, tenant):
        from rest_framework.test import APIClient

        _, user = login_as(role, tenant)
        client = APIClient()
        client.force_authenticate(user)
        return client

    @pytest.mark.parametrize(
        "path", ["members", "families", "tags", "event-registrations", "event-attendances",
                 "enrollments", "certificates"],
    )
    def test_plain_member_cannot_read_people_data(self, path, tenant, person):
        assert self._client("member", tenant).get(f"/api/v1/{path}/").status_code == 403

    def test_plain_member_can_still_read_the_event_and_course_catalogs(self, tenant):
        client = self._client("member", tenant)
        assert client.get("/api/v1/events/").status_code == 200
        assert client.get("/api/v1/courses/").status_code == 200

    def test_teacher_reads_enrollments_but_cannot_enrol(self, tenant, person):
        client = self._client("teacher", tenant)
        course = Course.objects.create(tenant=tenant, title="Fundamentos")
        assert client.get("/api/v1/enrollments/").status_code == 200
        response = client.post(
            "/api/v1/enrollments/", {"member": str(person.pk), "course": str(course.pk)}
        )
        assert response.status_code == 403

    def test_notes_are_only_in_the_payload_for_pastors_and_admins(self, tenant, person):
        volunteer = self._client("volunteer", tenant).get(f"/api/v1/members/{person.pk}/").json()
        pastor = self._client("pastor", tenant).get(f"/api/v1/members/{person.pk}/").json()
        assert "notes" not in volunteer and pastor["notes"] == NOTE

    def test_volunteer_cannot_overwrite_notes_through_the_api(self, tenant, person):
        client = self._client("volunteer", tenant)
        response = client.patch(
            f"/api/v1/members/{person.pk}/", {"notes": "x", "phone": "555-9999"}, format="json"
        )
        assert response.status_code == 200
        person.refresh_from_db()
        assert person.notes == NOTE and person.phone == "555-9999"

    def test_family_payload_hides_member_notes_too(self, tenant, person, family):
        payload = self._client("volunteer", tenant).get(f"/api/v1/families/{family.pk}/").json()
        assert "notes" not in payload
        assert all("notes" not in m for m in payload["members"])


@pytest.mark.django_db
class TestRosters:
    @pytest.fixture
    def course_with_student(self, tenant):
        block = CourseBlock.objects.create(tenant=tenant, name="Discipulado")
        course = Course.objects.create(tenant=tenant, title="Fundamentos", course_block=block)
        student = Member.objects.create(tenant=tenant, first_name="Zacarías", last_name="Roster")
        Enrollment.objects.create(tenant=tenant, member=student, course=course)
        return course, block

    def test_plain_member_sees_the_course_but_not_who_is_enrolled(self, tenant, course_with_student):
        course, block = course_with_student
        client, _ = login_as("member", tenant)
        for url in (reverse("course_detail", args=[course.pk]),
                    reverse("course_block_detail", args=[block.pk])):
            response = client.get(url)
            assert response.status_code == 200
            assert "Zacarías" not in response.content.decode()

    def test_teacher_sees_the_students_without_a_link_to_their_file(self, tenant, course_with_student):
        course, _ = course_with_student
        client, _ = login_as("teacher", tenant)
        page = client.get(reverse("course_detail", args=[course.pk])).content.decode()
        assert "Zacarías" in page
        assert "/members/" not in page.split("Miembros Inscritos")[1]

    def test_volunteer_sees_them_with_a_link(self, tenant, course_with_student):
        course, _ = course_with_student
        client, _ = login_as("volunteer", tenant)
        page = client.get(reverse("course_detail", args=[course.pk])).content.decode()
        assert "Zacarías" in page and "/members/" in page

    def test_event_registrations_are_for_member_managers_only(self, tenant, person):
        event = Event.objects.create(
            tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=3)
        )
        EventRegistration.objects.create(tenant=tenant, member=person, event=event)
        url = reverse("event_detail", args=[event.pk])

        member_client, _ = login_as("member", tenant)
        volunteer_client, _ = login_as("volunteer", tenant)

        member_page = member_client.get(url)
        assert member_page.status_code == 200
        assert "Marta" not in member_page.content.decode()
        assert "Marta" in volunteer_client.get(url).content.decode()


@pytest.mark.django_db
class TestCertificates:
    @pytest.fixture
    def certificate(self, tenant, person):
        block = CourseBlock.objects.create(tenant=tenant, name="Liderazgo")
        return BlockCertificate.objects.create(tenant=tenant, member=person, course_block=block)

    def test_a_member_cannot_open_someone_elses_certificate(self, tenant, certificate):
        client, _ = login_as("member", tenant)
        response = client.get(reverse("block_certificate_detail", args=[certificate.pk]))
        assert response.status_code == 404

    def test_the_owner_can_open_theirs(self, tenant, person, certificate):
        client, _ = login_as("member", tenant, member_profile=person)
        response = client.get(reverse("block_certificate_detail", args=[certificate.pk]))
        assert response.status_code == 200

    def test_staff_can_open_any(self, tenant, certificate):
        for role in ("admin", "teacher", "volunteer"):
            client, _ = login_as(role, tenant)
            response = client.get(reverse("block_certificate_detail", args=[certificate.pk]))
            assert response.status_code == 200, role


@pytest.mark.django_db
class TestDashboardAndNav:
    @pytest.fixture(autouse=True)
    def _onboarded(self, tenant, person):
        tenant.onboarding_completed = True
        tenant.save()

    def test_plain_member_gets_no_numbers_or_menus(self, tenant):
        client, _ = login_as("member", tenant)
        page = client.get(reverse("dashboard")).content.decode()
        assert "Total Miembros" not in page and "Donaciones del Mes" not in page
        assert "Miembros Recientes" not in page
        assert "Mi ficha" in page
        assert "Comunidad" not in page and "Finanzas" not in page

    def test_treasurer_sees_giving_but_not_the_membership(self, tenant):
        client, _ = login_as("treasurer", tenant)
        page = client.get(reverse("dashboard")).content.decode()
        assert "Donaciones del Mes" in page and "Total Miembros" not in page
        assert "Finanzas" in page and "Comunidad" not in page

    def test_pastor_sees_the_membership_but_not_the_giving(self, tenant):
        client, _ = login_as("pastor", tenant)
        page = client.get(reverse("dashboard")).content.decode()
        assert "Total Miembros" in page and "Donaciones del Mes" not in page
        assert "Comunidad" in page and "Finanzas" not in page

    def test_admin_sees_everything(self, tenant):
        client, _ = login_as("admin", tenant)
        page = client.get(reverse("dashboard")).content.decode()
        assert "Total Miembros" in page and "Donaciones del Mes" in page
        assert "Comunidad" in page and "Finanzas" in page

    def test_the_status_counts_are_right(self, tenant):
        Member.objects.create(tenant=tenant, first_name="V", last_name="1", member_status="visitor")
        client, _ = login_as("admin", tenant)
        response = client.get(reverse("dashboard"))
        context = response.context
        assert context["total_members"] == 2
        assert context["members_as_visitor"] >= 1
        assert (
            context["members_as_member"] + context["members_as_visitor"]
            + context["members_as_attendee"] + context["members_inactive"]
        ) == 2


@pytest.mark.django_db
class TestMyRecord:
    def test_requires_login(self):
        response = Client().get(reverse("my_record"))
        assert response.status_code == 302 and "login" in response.url

    def test_unlinked_user_is_told_to_ask_the_admin(self, tenant):
        client, _ = login_as("member", tenant)
        response = client.get(reverse("my_record"))
        assert response.status_code == 200
        assert "aún no está vinculado" in response.content.decode()

    def test_shows_only_the_linked_persons_data(self, tenant, person):
        block = CourseBlock.objects.create(tenant=tenant, name="Liderazgo")
        mine = Course.objects.create(tenant=tenant, title="Mi curso", course_block=block)
        Enrollment.objects.create(tenant=tenant, member=person, course=mine)
        stranger = Member.objects.create(tenant=tenant, first_name="Otra", last_name="Persona")
        Enrollment.objects.create(
            tenant=tenant, member=stranger, course=Course.objects.create(tenant=tenant, title="Ajeno")
        )
        Donation.objects.create(
            tenant=tenant, member=stranger, amount=Decimal("4242.00"), status="completed"
        )
        BlockCertificate.objects.create(tenant=tenant, member=person, course_block=block)
        event = Event.objects.create(
            tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=2)
        )
        EventRegistration.objects.create(tenant=tenant, member=person, event=event)
        client, _ = login_as("member", tenant, member_profile=person)

        page = client.get(reverse("my_record")).content.decode()

        assert "Marta Vargas" in page
        assert "Mi curso" in page and "Liderazgo" in page and "Retiro" in page
        assert shows(page, 7, 777)
        assert "Ajeno" not in page and "Otra Persona" not in page and not shows(page, 4, 242)
        assert NOTE not in page

    def test_a_record_from_another_church_is_never_shown(self, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        foreign = Member.objects.create(tenant=other, first_name="Foránea", last_name="X")
        client, _ = login_as("member", tenant, member_profile=foreign)
        page = client.get(reverse("my_record")).content.decode()
        assert "Foránea" not in page and "aún no está vinculado" in page

    def test_can_update_only_contact_details(self, tenant, person):
        client, _ = login_as("member", tenant, member_profile=person)

        response = client.post(
            reverse("my_record_edit"),
            {"phone": "555-7777", "city": "Heredia", "first_name": "Hacker",
             "member_status": "inactive", "notes": "mío"},
        )

        assert response.status_code == 302
        person.refresh_from_db()
        assert person.phone == "555-7777" and person.city == "Heredia"
        assert person.first_name == "Marta" and person.member_status != "inactive"
        assert person.notes == NOTE

    def test_unlinked_user_cannot_open_the_edit_form(self, tenant):
        client, _ = login_as("member", tenant)
        assert client.get(reverse("my_record_edit")).status_code == 404


@pytest.mark.django_db
class TestLinkingUsersToMembers:
    def _data(self, **overrides):
        data = {
            "first_name": "Ana", "last_name": "Mora", "email": "ana@iglesia.test",
            "role": "member", "password1": STRONG, "password2": STRONG,
        }
        data.update(overrides)
        return data

    def test_admin_can_pick_the_member_when_creating_the_login(
        self, authenticated_client, admin_user, person
    ):
        response = authenticated_client.post(
            reverse("user_create"), self._data(member_profile=str(person.pk))
        )
        assert response.status_code == 302
        assert User.objects.get(email="ana@iglesia.test").member_profile == person

    def test_a_free_member_with_the_same_email_is_linked_automatically(
        self, authenticated_client, admin_user, tenant
    ):
        match = Member.objects.create(
            tenant=tenant, first_name="Ana", last_name="Mora", email="ANA@iglesia.test"
        )
        authenticated_client.post(reverse("user_create"), self._data())
        assert User.objects.get(email="ana@iglesia.test").member_profile == match

    def test_without_a_match_the_login_stays_unlinked(self, authenticated_client, admin_user):
        authenticated_client.post(reverse("user_create"), self._data())
        assert User.objects.get(email="ana@iglesia.test").member_profile is None

    def test_cannot_pick_a_member_of_another_church_or_one_already_linked(
        self, authenticated_client, admin_user, tenant, person
    ):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        foreign = Member.objects.create(tenant=other, first_name="F", last_name="X")
        login_as("member", tenant, member_profile=person)  # `person` is taken now

        for member in (foreign, person):
            response = authenticated_client.post(
                reverse("user_create"), self._data(member_profile=str(member.pk))
            )
            assert response.status_code == 200  # form re-rendered with an error
        assert not User.objects.filter(email="ana@iglesia.test").exists()

    def test_edit_can_link_and_unlink(self, authenticated_client, admin_user, tenant, person):
        _, target = login_as("member", tenant)
        url = reverse("user_update", args=[target.pk])
        base = {"first_name": "A", "last_name": "B", "role": "member", "is_active": "on"}

        authenticated_client.post(url, {**base, "member_profile": str(person.pk)})
        target.refresh_from_db()
        assert target.member_profile == person

        authenticated_client.post(url, {**base, "member_profile": ""})
        target.refresh_from_db()
        assert target.member_profile is None


@pytest.mark.django_db
class TestFinanceScreensForTreasurers:
    """A treasurer sees donors' names but cannot open the member directory, so
    those names must not be links to a page that answers 403."""

    def test_donation_pages_show_names_without_member_links(self, tenant, person):
        donation = Donation.objects.get(member=person)
        treasurer, _ = login_as("treasurer", tenant)
        admin, _ = login_as("admin", tenant)
        member_url = reverse("member_detail", args=[person.pk])

        for name, args in (("donation_list", []), ("donation_detail", [donation.pk]),
                           ("donations_by_member", [])):
            treasurer_page = treasurer.get(reverse(name, args=args)).content.decode()
            admin_page = admin.get(reverse(name, args=args)).content.decode()
            assert "Marta Vargas" in treasurer_page and member_url not in treasurer_page, name
            assert member_url in admin_page, name
