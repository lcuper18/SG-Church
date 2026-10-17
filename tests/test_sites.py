"""
Sites (sedes): a church can meet in several places; events and members carry
one, single-site churches never see any of it, and reports can use it.
"""

import importlib
import uuid
from datetime import timedelta
from io import StringIO

import pytest
from django.apps import apps as django_apps
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from members import importer
from members.models import Member, User
from tenants.models import Site, Tenant

STRONG = "Clave-Segura-2026"


def login_as(role, tenant):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role, tenant=tenant
    )
    client = Client()
    client.force_login(user)
    return client


def soon(days=3):
    return timezone.now() + timedelta(days=days)


def event_form(**overrides):
    data = {
        "title": "Culto", "event_type": "service", "location": "", "start_at": "2030-05-10T18:00",
        "is_active": "on",
    }
    data.update(overrides)
    return data


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.fixture
def north(tenant):
    return Site.objects.create(tenant=tenant, name="Sede Norte", address="Avenida Norte")


@pytest.mark.django_db
class TestSiteModel:
    def test_every_church_starts_with_one_main_site(self, tenant):
        sites = list(Site.objects.filter(tenant=tenant))
        assert [(s.name, s.is_main) for s in sites] == [("Sede principal", True)]
        assert tenant.main_site() == sites[0]

    def test_main_site_is_recreated_or_promoted_when_missing(self, tenant):
        Site.all_objects.filter(tenant=tenant).delete()
        assert tenant.main_site().is_main
        Site.objects.create(tenant=tenant, name="Otra")
        Site.objects.filter(is_main=True, tenant=tenant).update(is_main=False)
        assert tenant.main_site().is_main
        assert Site.objects.filter(tenant=tenant, is_main=True).count() == 1

    def test_uses_sites_only_with_two_or_more_active(self, tenant):
        assert tenant.uses_sites is False
        extra = Site.objects.create(tenant=tenant, name="Norte")
        tenant.__dict__.pop("uses_sites", None)
        assert tenant.uses_sites is True
        extra.is_active = False
        extra.save()
        tenant.__dict__.pop("uses_sites", None)
        assert tenant.uses_sites is False

    def test_names_are_unique_among_live_sites_only(self, tenant):
        norte = Site.objects.create(tenant=tenant, name="Norte")
        with pytest.raises(IntegrityError), transaction.atomic():
            Site.objects.create(tenant=tenant, name="Norte")
        norte.delete()
        Site.objects.create(tenant=tenant, name="Norte")  # the trashed one doesn't block it

    def test_same_name_in_two_churches_is_fine(self, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        Site.objects.create(tenant=tenant, name="Norte")
        Site.objects.create(tenant=other, name="Norte")

    def test_only_one_main_site_per_church(self, tenant):
        with pytest.raises(IntegrityError), transaction.atomic():
            Site.objects.create(tenant=tenant, name="Segunda", is_main=True)

    def test_blockers_explain_why_a_site_cannot_go(self, tenant, north):
        assert north.blockers() == []
        Event.objects.create(tenant=tenant, title="Culto", start_at=soon(), site=north)
        Member.objects.create(tenant=tenant, first_name="A", last_name="B", home_site=north)
        reasons = " ".join(north.blockers())
        assert "1 evento(s) próximos" in reasons and "1 miembro(s)" in reasons
        assert "principal" in " ".join(tenant.main_site().blockers())

    def test_events_without_a_site_land_on_the_main_one(self, tenant):
        event = Event.objects.create(tenant=tenant, title="Culto", start_at=soon())
        assert event.site == tenant.main_site()

    def test_the_backfill_migration_function_fixes_old_data(self, tenant):
        migration = importlib.import_module("events.migrations.0007_backfill_event_sites")
        old = Event.objects.create(tenant=tenant, title="Viejo", start_at=soon())
        Event.objects.filter(pk=old.pk).update(site=None)
        Site.all_objects.filter(tenant=tenant).delete()

        migration.give_every_church_a_main_site(django_apps, None)

        old.refresh_from_db()
        assert old.site.is_main and old.site.tenant_id == tenant.pk


@pytest.mark.django_db
class TestSitesScreen:
    def test_only_church_admins(self, tenant):
        for role in ("pastor", "treasurer", "teacher", "volunteer", "member"):
            client = login_as(role, tenant)
            assert client.get(reverse("site_list")).status_code == 403, role
            assert client.get(reverse("site_create")).status_code == 403, role
        assert Client().get(reverse("site_list")).status_code == 302

    def test_create_edit_and_list_with_counts(self, authenticated_client, tenant):
        response = authenticated_client.post(
            reverse("site_create"), {"name": "Sede Sur", "address": "Calle Sur", "phone": "", "is_active": "on", "sort_order": 2}
        )
        assert response.status_code == 302
        sur = Site.objects.get(name="Sede Sur")
        Member.objects.create(tenant=tenant, first_name="Ana", last_name="Sur", home_site=sur)

        authenticated_client.post(
            reverse("site_update", args=[sur.pk]),
            {"name": "Sede Sur 2", "address": "", "phone": "", "is_active": "on", "sort_order": 2},
        )

        listing = authenticated_client.get(reverse("site_list")).context["sites"]
        row = next(s for s in listing if s.pk == sur.pk)
        assert row.name == "Sede Sur 2" and row.member_total == 1 and row.event_total == 0

    def test_duplicate_names_are_refused(self, authenticated_client, north):
        response = authenticated_client.post(
            reverse("site_create"), {"name": "sede norte", "address": "", "phone": "", "is_active": "on", "sort_order": 0}
        )
        assert response.status_code == 200 and "Ya tienes una sede con ese nombre" in response.content.decode()

    def test_the_main_site_cannot_be_deactivated(self, authenticated_client, tenant):
        main = tenant.main_site()
        authenticated_client.post(
            reverse("site_update", args=[main.pk]), {"name": "Central", "address": "", "phone": "", "sort_order": 0}
        )
        main.refresh_from_db()
        assert main.name == "Central" and main.is_active

    def test_delete_is_refused_when_in_use_and_goes_to_the_trash_otherwise(self, authenticated_client, tenant, north):
        Event.objects.create(tenant=tenant, title="Culto", start_at=soon(), site=north)
        response = authenticated_client.post(reverse("site_delete", args=[north.pk]), follow=True)
        assert "No se puede eliminar" in response.content.decode() and Site.objects.filter(pk=north.pk).exists()

        authenticated_client.post(reverse("site_delete", args=[tenant.main_site().pk]))
        assert tenant.main_site().is_main  # still there

        Event.objects.filter(tenant=tenant).delete()
        authenticated_client.post(reverse("site_delete", args=[north.pk]))
        assert Site.all_objects.get(pk=north.pk).is_deleted

    def test_other_churches_sites_are_untouchable(self, authenticated_client):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        theirs = other.main_site()
        assert authenticated_client.get(reverse("site_update", args=[theirs.pk])).status_code == 404
        assert authenticated_client.post(reverse("site_delete", args=[theirs.pk])).status_code == 404

    def test_trashed_sites_can_be_restored_from_the_trash(self, authenticated_client, north):
        north.delete()
        authenticated_client.post(reverse("trash_restore", args=["tenants.site", north.pk]))
        assert Site.objects.filter(pk=north.pk).exists()


@pytest.mark.django_db
class TestEventsAndSites:
    def test_a_single_site_church_sees_no_site_ui(self, authenticated_client, tenant):
        assert 'name="site"' not in authenticated_client.get(reverse("event_create")).content.decode()
        authenticated_client.post(reverse("event_create"), event_form())
        assert Event.objects.get().site == tenant.main_site()
        page = authenticated_client.get(reverse("event_list")).content.decode()
        assert "Todas las sedes" not in page and "<th>Sede</th>" not in page

    def test_with_two_sites_the_form_asks_and_the_list_shows_and_filters(self, authenticated_client, tenant, north):
        form = authenticated_client.get(reverse("event_create")).content.decode()
        assert 'id="site"' in form and "Sede Norte" in form and "(principal)" in form

        authenticated_client.post(reverse("event_create"), event_form(title="Culto Norte", site=str(north.pk)))
        authenticated_client.post(reverse("event_create"), event_form(title="Culto Central"))
        assert Event.objects.get(title="Culto Norte").site == north
        assert Event.objects.get(title="Culto Central").site == tenant.main_site()

        listing = authenticated_client.get(reverse("event_list"))
        assert "Todas las sedes" in listing.content.decode()
        only_north = authenticated_client.get(reverse("event_list"), {"site": str(north.pk)})
        assert [e.title for e in only_north.context["events"]] == ["Culto Norte"]
        assert authenticated_client.get(reverse("event_list"), {"site": "basura"}).status_code == 200

    def test_cannot_pick_another_churchs_site(self, authenticated_client, tenant, north):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        response = authenticated_client.post(
            reverse("event_create"), event_form(site=str(other.main_site().pk))
        )
        assert response.status_code == 200 and not Event.objects.exists()

    def test_inactive_sites_are_hidden_from_new_events_but_kept_on_old_ones(self, authenticated_client, tenant, north):
        event = Event.objects.create(tenant=tenant, title="Culto", start_at=soon(), site=north)
        Site.objects.create(tenant=tenant, name="Cerrada", is_active=False)
        north.is_active = False
        north.save()
        tenant.__dict__.pop("uses_sites", None)
        Site.objects.create(tenant=tenant, name="Sede Sur")  # keeps the church multi-site

        creating = authenticated_client.get(reverse("event_create")).content.decode()
        editing = authenticated_client.get(reverse("event_update", args=[event.pk])).content.decode()

        assert "Cerrada" not in creating and "Sede Norte" not in creating
        assert "Sede Norte" in editing  # the event's own site stays selectable

    def test_the_detail_page_names_the_site(self, authenticated_client, tenant, north):
        event = Event.objects.create(tenant=tenant, title="Culto", start_at=soon(), site=north)
        assert "Sede Norte" in authenticated_client.get(reverse("event_detail", args=[event.pk])).content.decode()


@pytest.mark.django_db
class TestMembersAndSites:
    def test_home_site_field_only_appears_with_several_sites(self, authenticated_client, tenant):
        assert 'name="home_site"' not in authenticated_client.get(reverse("member_create")).content.decode()
        Site.objects.create(tenant=tenant, name="Norte")
        tenant.__dict__.pop("uses_sites", None)
        assert 'name="home_site"' in authenticated_client.get(reverse("member_create")).content.decode()

    def test_set_filter_export_and_detail(self, authenticated_client, tenant, north):
        authenticated_client.post(
            reverse("member_create"),
            {"first_name": "Ana", "last_name": "Norte", "member_status": "member", "home_site": str(north.pk)},
        )
        Member.objects.create(tenant=tenant, first_name="Beto", last_name="Central")
        ana = Member.objects.get(first_name="Ana")
        assert ana.home_site == north

        only = authenticated_client.get(reverse("member_list"), {"site": str(north.pk)}).context["members"]
        assert [m.first_name for m in only] == ["Ana"]
        assert "Sede de origen" in authenticated_client.get(reverse("member_detail", args=[ana.pk])).content.decode()
        export = authenticated_client.get(reverse("member_export")).content.decode("utf-8")
        assert export.splitlines()[0].endswith("Sede") and "Sede Norte" in export

    def test_another_churchs_site_is_rejected_in_the_form_and_the_api(self, authenticated_client, authenticated_api_client, tenant, north):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        foreign = str(other.main_site().pk)
        response = authenticated_client.post(
            reverse("member_create"),
            {"first_name": "X", "last_name": "Y", "member_status": "member", "home_site": foreign},
        )
        assert response.status_code == 200 and not Member.objects.filter(first_name="X").exists()
        api = authenticated_api_client.post(
            "/api/v1/members/", {"first_name": "X", "last_name": "Y", "home_site": foreign}, format="json"
        )
        assert api.status_code == 400

    def test_the_csv_import_reads_the_site_column(self, tenant, north):
        plan = importer.build_plan(
            "Nombre,Apellido,Sede\nAna,Mora,sede norte\nBeto,Solís,Sede Fantasma\nCarla,Rojas,\n".encode(), tenant
        )
        assert [r.action for r in plan.rows] == ["create"] * 3
        assert plan.rows[0].warnings == [] and "no existe" in plan.rows[1].warnings[0]

        importer.apply_plan(plan, tenant, None)

        assert Member.objects.get(first_name="Ana").home_site == north
        assert Member.objects.get(first_name="Beto").home_site is None
        assert "Sede" in importer.TEMPLATE_HEADER
        assert len(importer.TEMPLATE_HEADER) == len(importer.TEMPLATE_EXAMPLE)

    def test_the_preview_shows_site_warnings(self, authenticated_client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = authenticated_client.post(
            reverse("member_import"),
            {"file": SimpleUploadedFile("a.csv", "Nombre,Apellido,Sede\nAna,Mora,Marte\n".encode()), "policy": "skip"},
        )
        assert "La sede «Marte» no existe" in response.content.decode()


@pytest.mark.django_db
class TestApi:
    def test_event_site_in_the_payload_filter_and_default(self, authenticated_api_client, tenant, north):
        authenticated_api_client.post(
            "/api/v1/events/",
            {"title": "Norte", "event_type": "service", "start_at": "2030-05-10T18:00:00Z", "site": str(north.pk)},
            format="json",
        )
        authenticated_api_client.post(
            "/api/v1/events/", {"title": "Sin sede", "event_type": "service", "start_at": "2030-05-11T18:00:00Z"},
            format="json",
        )
        everything = authenticated_api_client.get("/api/v1/events/").json()["results"]
        by_title = {e["title"]: e for e in everything}
        assert by_title["Norte"]["site_name"] == "Sede Norte"
        assert by_title["Sin sede"]["site_name"] == "Sede principal"

        filtered = authenticated_api_client.get("/api/v1/events/", {"site": str(north.pk)}).json()["results"]
        assert [e["title"] for e in filtered] == ["Norte"]
        assert authenticated_api_client.get("/api/v1/events/", {"site": "x"}).json()["results"] == []

    def test_cannot_create_an_event_in_another_churchs_site(self, authenticated_api_client, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        response = authenticated_api_client.post(
            "/api/v1/events/",
            {"title": "X", "event_type": "service", "start_at": "2030-05-10T18:00:00Z", "site": str(other.main_site().pk)},
            format="json",
        )
        assert response.status_code == 400

    def test_sites_endpoint_is_read_only_and_scoped(self, authenticated_api_client, tenant, north):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        names = [s["name"] for s in authenticated_api_client.get("/api/v1/sites/").json()["results"]]
        assert names == ["Sede principal", "Sede Norte"] and other.main_site().name not in names[1:]
        assert authenticated_api_client.post("/api/v1/sites/", {"name": "X"}, format="json").status_code == 405


@pytest.mark.django_db(transaction=True)
def test_the_demo_seed_creates_three_sites_once(admin_user):
    tenant = admin_user.tenant
    call_command("seed_demo_data", tenant=tenant.subdomain, members=60, stdout=StringIO())

    names = sorted(Site.objects.filter(tenant=tenant).values_list("name", flat=True))
    assert names == ["Sede Central", "Sede Norte", "Sede Sur"]
    assert Event.objects.filter(tenant=tenant).values("site").distinct().count() == 3
    assert Member.objects.filter(tenant=tenant, home_site__isnull=False).count() > 30

    before = list(Event.objects.filter(tenant=tenant).order_by("pk").values_list("pk", "site_id"))
    call_command("seed_demo_data", tenant=tenant.subdomain, stdout=StringIO())
    assert list(Event.objects.filter(tenant=tenant).order_by("pk").values_list("pk", "site_id")) == before
    assert Site.objects.filter(tenant=tenant).count() == 3
