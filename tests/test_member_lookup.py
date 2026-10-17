"""
The people lookup (type-ahead pickers) and accent-insensitive member search.
"""

import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from education.models import Course, Enrollment
from events.models import Event, EventRegistration
from members.models import Family, Member, User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"


def login_as(role, tenant):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role, tenant=tenant
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


def person(tenant, first, last, **kwargs):
    return Member.objects.create(tenant=tenant, first_name=first, last_name=last, **kwargs)


def lookup(client, **params):
    return client.get(reverse("member_lookup"), params)


def names(response):
    return [row["name"] for row in response.json()["results"]]


@pytest.mark.django_db
class TestAccess:
    def test_anonymous_is_sent_to_login(self):
        assert lookup(Client()).status_code == 302

    def test_plain_members_are_refused(self, tenant):
        assert lookup(login_as("member", tenant)).status_code == 403

    @pytest.mark.parametrize("role", ["admin", "pastor", "volunteer", "teacher", "treasurer"])
    def test_staff_roles_can_search(self, role, tenant):
        person(tenant, "Ana", "Mora")
        assert names(lookup(login_as(role, tenant))) == ["Ana Mora"]

    def test_other_churchs_people_never_show_up(self, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        person(other, "Foránea", "Ajena")
        person(tenant, "Local", "Propia")
        assert names(lookup(login_as("admin", tenant))) == ["Local Propia"]


@pytest.mark.django_db
class TestSearch:
    def test_ignores_accents_and_case(self, tenant):
        person(tenant, "Carlos", "Solís")
        client = login_as("admin", tenant)
        for text in ("solis", "SOLÍS", "sólis", "carlos solis"):
            assert names(lookup(client, q=text)) == ["Carlos Solís"], text

    def test_every_word_must_match(self, tenant):
        person(tenant, "María", "García")
        person(tenant, "María", "López")
        client = login_as("admin", tenant)
        assert names(lookup(client, q="maria garcia")) == ["María García"]
        assert names(lookup(client, q="maria")) == ["María García", "María López"]

    def test_finds_by_email_and_phone(self, tenant):
        person(tenant, "Ana", "Mora", email="ana.mora@iglesia.org", phone="+506 8888 1234")
        client = login_as("admin", tenant)
        assert names(lookup(client, q="iglesia.org")) == ["Ana Mora"]
        assert names(lookup(client, q="8888 1234")) == ["Ana Mora"]

    def test_search_text_follows_edits(self, tenant):
        ana = person(tenant, "Ana", "Mora")
        ana.last_name = "Núñez"
        ana.save(update_fields=["last_name"])
        client = login_as("admin", tenant)
        assert names(lookup(client, q="nunez")) == ["Ana Núñez"]
        assert names(lookup(client, q="mora")) == []

    def test_limit_total_and_caps(self, tenant):
        for index in range(20):
            person(tenant, f"Persona{index:02d}", "Prueba")
        client = login_as("admin", tenant)

        data = lookup(client).json()
        assert len(data["results"]) == 15 and data["total"] == 20

        assert len(lookup(client, limit=100).json()["results"]) == 20
        assert len(lookup(client, limit=3).json()["results"]) == 3
        assert len(lookup(client, limit="abc").json()["results"]) == 15

    def test_member_list_search_uses_the_same_rules(self, tenant):
        person(tenant, "María", "García")
        person(tenant, "Pedro", "Solís")
        client = login_as("admin", tenant)

        found = client.get(reverse("member_list"), {"search": "maria garcia"}).context["members"]
        assert [m.full_name for m in found] == ["María García"]
        found = client.get(reverse("member_list"), {"search": "solis"}).context["members"]
        assert [m.full_name for m in found] == ["Pedro Solís"]


@pytest.mark.django_db
class TestExclusions:
    def test_registered_people_are_hidden_for_that_event_only(self, tenant):
        inside, outside, cancelled = (
            person(tenant, "Dentro", "Inscrito"),
            person(tenant, "Fuera", "Libre"),
            person(tenant, "Cancelado", "Antes"),
        )
        event = Event.objects.create(
            tenant=tenant, title="Retiro", start_at=timezone.now() + timedelta(days=3)
        )
        EventRegistration.objects.create(tenant=tenant, member=inside, event=event)
        EventRegistration.objects.create(
            tenant=tenant, member=cancelled, event=event, status="cancelled"
        )
        client = login_as("admin", tenant)

        found = names(lookup(client, exclude_event=str(event.pk)))

        assert "Dentro Inscrito" not in found
        assert "Fuera Libre" in found and "Cancelado Antes" in found
        assert "Dentro Inscrito" in names(lookup(client))

    def test_enrolled_people_are_hidden_but_dropped_ones_are_not(self, tenant):
        enrolled, dropped = person(tenant, "Activa", "Alumna"), person(tenant, "Baja", "Alumno")
        course = Course.objects.create(tenant=tenant, title="Fundamentos")
        Enrollment.objects.create(tenant=tenant, member=enrolled, course=course)
        Enrollment.objects.create(tenant=tenant, member=dropped, course=course, status="dropped")

        found = names(lookup(login_as("admin", tenant), exclude_course=str(course.pk)))

        assert "Activa Alumna" not in found and "Baja Alumno" in found

    def test_a_malformed_id_excludes_nobody(self, tenant):
        person(tenant, "Ana", "Mora")
        assert names(lookup(login_as("admin", tenant), exclude_event="no-es-un-uuid")) == ["Ana Mora"]


@pytest.mark.django_db
class TestPagesDoNotShipTheDirectory:
    """The pickers fetch matches on demand, so these pages stay small however
    many people the church has."""

    @pytest.fixture
    def crowd(self, tenant):
        for index in range(40):
            person(tenant, f"Zeta{index:02d}", "Multitud")
        return tenant

    def test_event_page(self, crowd):
        event = Event.objects.create(
            tenant=crowd, title="Retiro", start_at=timezone.now() + timedelta(days=3)
        )
        page = login_as("admin", crowd).get(reverse("event_detail", args=[event.pk])).content.decode()
        assert "Multitud" not in page and 'data-url="/members/lookup/"' in page

    def test_course_page(self, crowd):
        course = Course.objects.create(tenant=crowd, title="Fundamentos")
        page = login_as("admin", crowd).get(reverse("course_detail", args=[course.pk])).content.decode()
        assert "Multitud" not in page and 'data-url="/members/lookup/"' in page

    def test_family_form_lists_only_the_chosen_members(self, crowd):
        family = Family.objects.create(tenant=crowd, name="Familia Z")
        member = Member.objects.filter(tenant=crowd).first()
        member.family = family
        member.save()
        page = login_as("admin", crowd).get(reverse("family_update", args=[family.pk])).content.decode()
        # Only the one chosen person: chip label, its "remove" aria-label and
        # its option in the head-of-family select. The other 39 aren't sent.
        assert page.count("Multitud") == 3
        assert page.count('name="members"') == 1
