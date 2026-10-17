"""
National ID (cédula, DNI...): tells apart people who share a name, is unique
per church, searchable, printed on certificates and part of the CSV import.
"""

import io
import uuid
from datetime import date

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from pypdf import PdfReader

from core.models import AuditLog
from education.certificates import render_certificate_pdf
from education.models import Course, CourseBlock, Enrollment
from members import importer
from members.models import Member, User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"


def login_as(role, tenant):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role, tenant=tenant
    )
    client = Client()
    client.force_login(user)
    return client


def person(tenant, first="Juan", last="Pérez", national_id="", **kwargs):
    return Member.objects.create(
        tenant=tenant, first_name=first, last_name=last, national_id=national_id, **kwargs
    )


def form_data(**overrides):
    data = {"first_name": "Juan", "last_name": "Pérez", "member_status": "member"}
    data.update(overrides)
    return data


@pytest.fixture
def tenant(admin_user):
    admin_user.tenant.country = "CR"
    admin_user.tenant.save()
    return admin_user.tenant


@pytest.mark.django_db
class TestUniqueness:
    def test_formats_of_the_same_number_are_the_same_id(self, tenant):
        person(tenant, national_id="1-1234-5678")
        assert Member.objects.get().national_id_key == "112345678"

        other = Member(tenant=tenant, first_name="Otro", last_name="Juan", national_id=" 1 1234 5678 ")
        with pytest.raises(IntegrityError), transaction.atomic():
            other.save()

    def test_homonyms_are_fine_when_their_ids_differ_or_are_empty(self, tenant):
        person(tenant, national_id="1-1111-1111")
        person(tenant, national_id="2-2222-2222")
        person(tenant)  # no ID (a child, say)
        person(tenant)
        assert Member.objects.filter(tenant=tenant, first_name="Juan").count() == 4

    def test_the_same_id_may_exist_in_two_churches(self, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        person(tenant, national_id="1-1234-5678")
        person(other, national_id="1-1234-5678")

    def test_a_trashed_person_frees_their_id(self, tenant):
        old = person(tenant, national_id="1-1234-5678")
        old.delete()
        person(tenant, first="Nuevo", national_id="1-1234-5678")  # no error

    def test_restoring_over_a_taken_id_explains_instead_of_crashing(self, authenticated_client, tenant):
        old = person(tenant, national_id="1-1234-5678")
        old.delete()
        person(tenant, first="Nuevo", national_id="1-1234-5678")

        response = authenticated_client.post(
            reverse("trash_restore", args=["members.member", old.pk]), follow=True
        )

        assert "ya existe otro registro" in response.content.decode()
        assert Member.all_objects.get(pk=old.pk).is_deleted


@pytest.mark.django_db
class TestWebForms:
    def test_create_with_an_id(self, authenticated_client, tenant):
        response = authenticated_client.post(reverse("member_create"), form_data(national_id="1-1234-5678"))
        assert response.status_code == 302
        assert Member.objects.get().national_id == "1-1234-5678"

    def test_a_duplicate_id_is_refused_naming_who_has_it(self, authenticated_client, tenant):
        person(tenant, first="María", last="Mora", national_id="1-1234-5678")

        response = authenticated_client.post(reverse("member_create"), form_data(national_id="112345678"))

        assert response.status_code == 200
        assert "ya pertenece a María Mora" in response.content.decode()
        assert Member.objects.filter(tenant=tenant).count() == 1

    def test_editing_someone_without_touching_their_id_is_fine(self, authenticated_client, tenant):
        ana = person(tenant, first="Ana", national_id="1-1234-5678")
        response = authenticated_client.post(
            reverse("member_update", args=[ana.pk]),
            form_data(first_name="Ana", national_id="1-1234-5678", phone="555"),
        )
        assert response.status_code == 302
        ana.refresh_from_db()
        assert ana.phone == "555"

    def test_clearing_an_id_is_allowed(self, authenticated_client, tenant):
        ana = person(tenant, first="Ana", national_id="1-1234-5678")
        authenticated_client.post(reverse("member_update", args=[ana.pk]), form_data(first_name="Ana"))
        ana.refresh_from_db()
        assert ana.national_id == "" and ana.national_id_key == ""

    def test_the_form_asks_with_the_countrys_word_for_it(self, authenticated_client, tenant):
        page = authenticated_client.get(reverse("member_create")).content.decode()
        assert 'for="national_id"' in page and "Cédula" in page


@pytest.mark.django_db
class TestLabelPerCountry:
    @pytest.mark.parametrize(
        "country, expected",
        [("CR", "Cédula"), ("AR", "DNI"), ("CL", "RUT"), ("GT", "DPI"), ("US", "Identificación"), (None, "Identificación")],
    )
    def test_default_label(self, tenant, country, expected):
        tenant.country = country
        assert tenant.id_label == expected

    def test_the_church_can_name_it_itself(self, authenticated_client, tenant):
        tenant.national_id_label = "Documento de identidad"
        tenant.save()
        ana = person(tenant, first="Ana", national_id="9-9999-9999")
        for url in (reverse("member_list"), reverse("member_detail", args=[ana.pk])):
            assert "Documento de identidad" in authenticated_client.get(url).content.decode()

    def test_admin_sets_the_label_in_settings(self, authenticated_client, tenant):
        authenticated_client.post(
            reverse("church_settings"),
            {
                "name": tenant.name, "denomination": "", "country": "CR", "city": "", "state": "",
                "address": "", "phone": "", "email": "", "currency": tenant.currency,
                "timezone": tenant.timezone, "enable_families": "on", "enable_tags": "on",
                "national_id_label": "DIMEX", "certificate_signer_name": "", "certificate_signer_title": "",
            },
        )
        tenant.refresh_from_db()
        assert tenant.id_label == "DIMEX"


@pytest.mark.django_db
class TestShowingAndSearching:
    def test_detail_and_list_show_the_id(self, authenticated_client, tenant):
        ana = person(tenant, first="Ana", national_id="1-1234-5678")
        assert "1-1234-5678" in authenticated_client.get(reverse("member_detail", args=[ana.pk])).content.decode()
        assert "1-1234-5678" in authenticated_client.get(reverse("member_list")).content.decode()

    def test_list_search_finds_by_id_with_or_without_hyphens(self, authenticated_client, tenant):
        person(tenant, first="Ana", national_id="1-1234-5678")
        person(tenant, first="Beto", national_id="2-0000-0001")
        for text in ("1-1234-5678", "112345678", "1234"):
            found = authenticated_client.get(reverse("member_list"), {"search": text}).context["members"]
            assert [m.first_name for m in found] == ["Ana"], text

    def test_pickers_show_only_the_last_digits_to_tell_homonyms_apart(self, tenant):
        person(tenant, national_id="1-1234-5678")
        person(tenant, national_id="2-0000-9999")

        rows = login_as("admin", tenant).get(reverse("member_lookup"), {"q": "juan"}).json()["results"]

        assert sorted(r["id_hint"] for r in rows) == ["···5678", "···9999"]
        assert "1-1234-5678" not in str(rows)

    def test_the_portal_shows_a_member_their_own_id(self, tenant):
        ana = person(tenant, first="Ana", national_id="1-1234-5678")
        client = Client()
        user = User.objects.create_user(
            email="ana@t.com", password=STRONG, role="member", tenant=tenant, member_profile=ana
        )
        client.force_login(user)
        assert "1-1234-5678" in client.get(reverse("my_record")).content.decode()

    def test_the_csv_export_has_the_column(self, authenticated_client, tenant):
        person(tenant, first="Ana", national_id="1-1234-5678")
        text = authenticated_client.get(reverse("member_export")).content.decode("utf-8")
        assert "Identificación" in text.splitlines()[0] and "1-1234-5678" in text


@pytest.mark.django_db
class TestApi:
    def test_create_and_reject_duplicates(self, authenticated_api_client, tenant):
        payload = {"first_name": "Ana", "last_name": "Mora", "national_id": "1-1234-5678"}
        assert authenticated_api_client.post("/api/v1/members/", payload, format="json").status_code == 201

        again = authenticated_api_client.post(
            "/api/v1/members/", {**payload, "first_name": "Otra", "national_id": "112345678"}, format="json"
        )
        assert again.status_code == 400 and "ya pertenece a Ana Mora" in str(again.json())

    def test_patching_someone_else_to_a_taken_id_fails_but_their_own_is_fine(self, authenticated_api_client, tenant):
        ana = person(tenant, first="Ana", national_id="1-1234-5678")
        beto = person(tenant, first="Beto", national_id="2-0000-0001")
        url = "/api/v1/members/{}/"

        bad = authenticated_api_client.patch(url.format(beto.pk), {"national_id": "1-1234-5678"}, format="json")
        ok = authenticated_api_client.patch(url.format(ana.pk), {"national_id": "1-1234-5678"}, format="json")

        assert bad.status_code == 400 and ok.status_code == 200


@pytest.mark.django_db
class TestAuditTrail:
    def test_changes_to_the_id_are_logged_without_the_number(self, tenant):
        ana = person(tenant, first="Ana", national_id="1-1234-5678")
        ana.national_id = "9-9999-9999"
        ana.save()

        entry = AuditLog.objects.filter(object_id=str(ana.pk), action="update").latest("created_at")

        assert entry.changes == {"national_id": ["•••", "•••"]}
        assert "9999" not in str(entry.changes) and "national_id_key" not in entry.changes


@pytest.mark.django_db
class TestCertificates:
    def certificate(self, tenant, national_id):
        member = person(tenant, first="Lucía", last="Fernández", national_id=national_id)
        block = CourseBlock.objects.create(tenant=tenant, name="Discipulado")
        course = Course.objects.create(tenant=tenant, title="Fe", course_block=block)
        Enrollment.objects.create(tenant=tenant, member=member, course=course).mark_completed()
        return member.block_certificates.get()

    def text(self, certificate):
        return PdfReader(io.BytesIO(render_certificate_pdf(certificate))).pages[0].extract_text()

    def test_the_pdf_prints_the_id_with_the_local_name(self, tenant):
        assert "Cédula: 1-1234-5678" in self.text(self.certificate(tenant, "1-1234-5678"))

    def test_the_pdf_uses_the_churchs_own_label(self, tenant):
        tenant.national_id_label = "DIMEX"
        tenant.save()
        certificate = self.certificate(tenant, "155812345678")
        certificate.refresh_from_db()
        assert "DIMEX: 155812345678" in self.text(certificate)

    def test_no_id_no_line(self, tenant):
        assert "Cédula" not in self.text(self.certificate(tenant, ""))

    def test_the_printable_page_shows_it(self, authenticated_client, tenant):
        certificate = self.certificate(tenant, "1-1234-5678")
        page = authenticated_client.get(reverse("block_certificate_detail", args=[certificate.pk])).content.decode()
        assert "Cédula: 1-1234-5678" in page

    def test_the_public_check_shows_only_the_last_digits(self, tenant):
        certificate = self.certificate(tenant, "1-1234-5678")
        page = Client().get(reverse("certificate_verify", args=[certificate.certificate_number])).content.decode()
        assert "···5678" in page and "1-1234-5678" not in page and "112345678" not in page


@pytest.mark.django_db
class TestImport:
    def plan(self, tenant, *lines, **kw):
        return importer.build_plan(("\n".join(lines) + "\n").encode(), tenant, **kw)

    def test_the_column_is_recognised_under_several_names(self, tenant):
        for title in ("Cédula", "Identificación", "DNI", "Documento de identidad", "ID"):
            plan = self.plan(tenant, f"Nombre,Apellido,{title}", "Ana,Mora,1-1234-5678")
            assert plan.rows[0].data["national_id"] == "1-1234-5678", title
            assert plan.ignored_headers == []

    def test_same_name_different_ids_are_two_people_not_a_duplicate(self, tenant):
        person(tenant, national_id="1-1111-1111")
        plan = self.plan(tenant, "Nombre,Apellido,Cédula", "Juan,Pérez,2-2222-2222", "Juan,Pérez,3-3333-3333")
        assert [r.action for r in plan.rows] == ["create", "create"]

    def test_an_existing_id_is_a_duplicate_even_with_other_email_and_spelling(self, tenant):
        person(tenant, national_id="1-1234-5678", email="viejo@x.org")
        plan = self.plan(tenant, "Nombre,Apellido,Email,Cédula", "Juanito,Pérez,nuevo@x.org,112345678")
        assert plan.rows[0].action == "skip" and "Ya existe" in plan.rows[0].messages[0]

    def test_the_same_id_twice_in_the_file_is_imported_once(self, tenant):
        plan = self.plan(tenant, "Nombre,Apellido,Cédula", "Ana,Mora,1-1234-5678", "Anita,Mora,1 1234 5678")
        assert [r.action for r in plan.rows] == ["create", "skip"]

    def test_id_and_email_pointing_at_different_people_is_an_error(self, tenant):
        person(tenant, first="María", last="Uno", national_id="1-1111-1111")
        person(tenant, first="Pedro", last="Dos", email="pedro@x.org")
        plan = self.plan(tenant, "Nombre,Apellido,Email,Cédula", "X,Y,pedro@x.org,1-1111-1111")
        assert plan.rows[0].action == "error"
        assert "María Uno" in plan.rows[0].messages[0] and "Pedro Dos" in plan.rows[0].messages[0]

    def test_updating_never_swaps_an_existing_different_id(self, tenant):
        person(tenant, first="Ana", national_id="1-1111-1111", email="ana@x.org")
        plan = self.plan(
            tenant, "Nombre,Apellido,Email,Cédula", "Ana,Pérez,ana@x.org,9-9999-9999", policy="update"
        )
        assert plan.rows[0].action == "error" and "otra identificación" in plan.rows[0].messages[0]

    def test_update_fills_in_a_missing_id(self, tenant):
        ana = person(tenant, first="Ana", email="ana@x.org")
        plan = self.plan(tenant, "Nombre,Apellido,Email,Cédula", "Ana,Pérez,ana@x.org,1-2345-6789", policy="update")
        importer.apply_plan(plan, tenant, None)
        ana.refresh_from_db()
        assert ana.national_id == "1-2345-6789" and ana.national_id_key == "123456789"

    def test_created_people_keep_their_id_and_a_round_trip_preserves_it(self, authenticated_client, tenant):
        person(tenant, first="Ana", last="Mora", national_id="1-1234-5678")
        exported = authenticated_client.get(reverse("member_export")).content
        other = Tenant.objects.create(name="Destino", subdomain=f"dest-{uuid.uuid4().hex[:6]}")

        importer.apply_plan(importer.build_plan(exported, other), other, None)

        assert Member.objects.get(tenant=other).national_id == "1-1234-5678"

    def test_the_template_includes_the_column(self):
        assert "Identificación" in importer.TEMPLATE_HEADER
        assert len(importer.TEMPLATE_HEADER) == len(importer.TEMPLATE_EXAMPLE)
