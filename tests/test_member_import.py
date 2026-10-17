"""
CSV import of members: reading messy spreadsheets, previewing before saving,
duplicates, and not letting anyone import more than they may.
"""

import csv
import io
import uuid
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from core.models import AuditLog
from members import importer
from members.models import Family, Member, Tag, User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"


def csv_bytes(*lines, encoding="utf-8"):
    return ("\n".join(lines) + "\n").encode(encoding)


def login_as(role, tenant):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role, tenant=tenant
    )
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


def plan_for(tenant, *lines, **kwargs):
    encoding = kwargs.pop("encoding", "utf-8")
    return importer.build_plan(csv_bytes(*lines, encoding=encoding), tenant, **kwargs)


@pytest.mark.django_db
class TestReadingTheFile:
    def test_matches_headers_loosely_and_reads_every_field(self, tenant):
        plan = plan_for(
            tenant,
            "NOMBRE,Apellidos,Correo,Celular,Cumpleaños,Sexo,Estado Civil,Bautizada,Estado,Familia,Etiquetas",
            "María,Rodríguez Mora,MARIA@Ejemplo.com,+506 8888 1234,17/05/1990,Femenino,Casada,sí,Miembro,"
            "Familia Rodríguez,\"Jóvenes; Alabanza\"",
        )

        (row,) = plan.rows
        assert row.action == "create"
        assert row.data == {
            "first_name": "María", "last_name": "Rodríguez Mora", "email": "maria@ejemplo.com",
            "phone": "+506 8888 1234", "date_of_birth": date(1990, 5, 17), "gender": "female",
            "marital_status": "married", "is_baptized": True, "member_status": "member",
        }
        assert row.family == "Familia Rodríguez" and row.tags == ["Jóvenes", "Alabanza"]
        assert plan.ignored_headers == []

    @pytest.mark.parametrize("delimiter", [";", "\t"])
    def test_detects_semicolon_and_tab_separated_files(self, tenant, delimiter):
        header = delimiter.join(["Nombre", "Apellido", "Email"])
        row = delimiter.join(["Ana", "Mora", "ana@x.org"])
        assert plan_for(tenant, header, row).rows[0].data["email"] == "ana@x.org"

    def test_reads_excels_windows_encoding_and_a_bom(self, tenant):
        old_excel = plan_for(tenant, "Nombre;Apellido", "José;Núñez", encoding="cp1252")
        assert old_excel.rows[0].label == "José Núñez"
        with_bom = plan_for(tenant, "﻿Nombre,Apellido", "Ana,Mora")
        assert with_bom.rows[0].action == "create"

    def test_accepts_our_own_export_including_protected_phones(self, tenant):
        # The export prefixes text starting with + with an apostrophe.
        plan = plan_for(tenant, "Nombre,Apellido,Teléfono", "Ana,Mora,'+506 8888 1234")
        assert plan.rows[0].data["phone"] == "+506 8888 1234"

    def test_unknown_columns_are_reported_and_ignored(self, tenant):
        plan = plan_for(tenant, "Nombre,Apellido,Color favorito", "Ana,Mora,azul")
        assert plan.ignored_headers == ["Color favorito"]
        assert "color favorito" not in plan.rows[0].data

    def test_blank_lines_are_skipped_and_row_numbers_match_the_sheet(self, tenant):
        plan = plan_for(tenant, "Nombre,Apellido", "Ana,Mora", ",", "Beto,Solís")
        assert [(r.number, r.label) for r in plan.rows] == [(2, "Ana Mora"), (4, "Beto Solís")]

    @pytest.mark.parametrize(
        "lines, fragment",
        [
            ((), "vacío"),
            (("Nombre,Apellido",), "sin ninguna persona"),
            (("Nombre,Email", "Ana,a@x.org"), "Apellido"),
            (("Correo,Teléfono", "a@x.org,1"), "Nombre y Apellido"),
        ],
    )
    def test_unusable_files_say_why(self, tenant, lines, fragment):
        with pytest.raises(importer.ImportFileError, match=fragment):
            plan_for(tenant, *lines)

    def test_too_many_rows_or_bytes_are_refused(self, tenant):
        rows = [f"P{i},Prueba" for i in range(importer.MAX_ROWS + 1)]
        with pytest.raises(importer.ImportFileError, match="Demasiadas filas"):
            plan_for(tenant, "Nombre,Apellido", *rows)
        with pytest.raises(importer.ImportFileError, match="demasiado grande"):
            importer.build_plan(b"x" * (importer.MAX_BYTES + 1), tenant)


@pytest.mark.django_db
class TestValidation:
    def test_each_problem_is_reported_against_its_row_and_others_still_go(self, tenant):
        plan = plan_for(
            tenant,
            "Nombre,Apellido,Email,Fecha de nacimiento,Género,Bautizado,Estado",
            "Ana,Mora,ana@x.org,1990-01-02,F,Sí,Miembro",
            ",Sinnombre,,,,,",
            "Beto,Solís,no-es-correo,,,,",
            "Carla,Rojas,,31/02/2000,,,",
            "Dani,Vega,,,marciano,,",
            "Eva,León,,,,quizá,",
            "Fer,Mora,,,,,casi",
        )

        actions = [r.action for r in plan.rows]
        assert actions == ["create"] + ["error"] * 6
        reasons = [" ".join(r.messages) for r in plan.rows[1:]]
        assert "Falta el Nombre" in reasons[0]
        assert "Correo no válido" in reasons[1]
        assert "Fecha no válida" in reasons[2]
        assert "Género" in reasons[3] and "no reconocido" in reasons[3]
        assert "Bautizado" in reasons[4]
        assert "Estado" in reasons[5]
        assert plan.importable == 1 and len(plan.errors) == 6

    def test_future_birth_dates_and_overlong_values_are_errors(self, tenant):
        plan = plan_for(
            tenant, "Nombre,Apellido,Fecha de nacimiento,Etiquetas",
            "Ana,Mora,2999-01-01,", f"{'x' * 101},Mora,,", f"Beto,Solís,,{'t' * 60}",
        )
        assert [r.action for r in plan.rows] == ["error", "error", "error"]

    def test_formula_looking_text_is_stored_as_plain_text(self, tenant):
        plan = plan_for(tenant, "Nombre,Apellido", "=HYPERLINK(\"x\"),Mora")
        assert plan.rows[0].data["first_name"].startswith("=")  # exports re-escape it


@pytest.mark.django_db
class TestDuplicates:
    @pytest.fixture
    def ana(self, tenant):
        return Member.objects.create(
            tenant=tenant, first_name="Ana", last_name="Mora", email="Ana@X.org", phone="111",
            is_baptized=True, city="Escazú",
        )

    def test_default_is_to_skip_people_who_already_exist(self, tenant, ana):
        plan = plan_for(tenant, "Nombre,Apellido,Email", "Anita,Mora,ana@x.org", "Beto,Solís,beto@x.org")
        assert [r.action for r in plan.rows] == ["skip", "create"]
        assert "Ya existe" in plan.rows[0].messages[0]

    def test_update_policy_fills_what_the_file_has_and_never_blanks(self, tenant, ana):
        plan = plan_for(
            tenant, "Nombre,Apellido,Email,Teléfono,Ciudad,Bautizado",
            "Ana,Mora,ana@x.org,222,,", policy="update",
        )
        assert plan.rows[0].action == "update"

        importer.apply_plan(plan, tenant, None)

        ana.refresh_from_db()
        assert ana.phone == "222"
        assert ana.city == "Escazú"  # empty cell: untouched
        assert ana.is_baptized is True  # empty cell: untouched
        assert Member.objects.filter(tenant=tenant).count() == 1

    def test_people_without_email_match_on_name_plus_phone_or_birth_date(self, tenant):
        Member.objects.create(tenant=tenant, first_name="Luis", last_name="Gómez", phone="555")
        Member.objects.create(tenant=tenant, first_name="Luis", last_name="Gómez", date_of_birth=date(1980, 1, 1))
        plan = plan_for(
            tenant, "Nombre,Apellido,Teléfono,Fecha de nacimiento",
            "Luis,Gómez,555,", "luis,gomez,,1980-01-01", "Luis,Gómez,999,1999-09-09",
        )
        assert [r.action for r in plan.rows] == ["skip", "skip", "create"]

    def test_a_repeated_line_in_the_file_is_imported_once(self, tenant):
        plan = plan_for(tenant, "Nombre,Apellido,Email", "Ana,Mora,a@x.org", "Ana,Mora,A@x.org")
        assert [r.action for r in plan.rows] == ["create", "skip"]

    def test_other_churches_people_are_not_duplicates(self, tenant):
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        Member.objects.create(tenant=other, first_name="Ana", last_name="Mora", email="ana@x.org")
        assert plan_for(tenant, "Nombre,Apellido,Email", "Ana,Mora,ana@x.org").rows[0].action == "create"

    def test_people_in_the_trash_do_not_count_as_existing(self, tenant, ana):
        ana.delete()
        assert plan_for(tenant, "Nombre,Apellido,Email", "Ana,Mora,ana@x.org").rows[0].action == "create"


@pytest.mark.django_db
class TestApplying:
    def test_creates_people_families_and_tags_reusing_existing_ones(self, tenant):
        existing_family = Family.objects.create(tenant=tenant, name="Familia Mora")
        existing_tag = Tag.objects.create(tenant=tenant, name="Jóvenes")
        plan = plan_for(
            tenant, "Nombre,Apellido,Familia,Etiquetas",
            "Ana,Mora,familia mora,jovenes",
            "Beto,Mora,Familia Nueva,\"Jóvenes, Coro\"",
        )

        counters = importer.apply_plan(plan, tenant, None)

        assert counters["created"] == 2
        assert counters["families_created"] == 1 and counters["tags_created"] == 1
        ana = Member.objects.get(first_name="Ana")
        assert ana.family == existing_family and list(ana.tags.all()) == [existing_tag]
        assert {t.name for t in Member.objects.get(first_name="Beto").tags.all()} == {"Jóvenes", "Coro"}
        assert Family.objects.filter(tenant=tenant).count() == 2

    def test_search_text_is_filled_so_imported_people_are_findable(self, tenant):
        importer.apply_plan(plan_for(tenant, "Nombre,Apellido", "Carlos,Solís"), tenant, None)
        assert Member.objects.get(first_name="Carlos").search_text.startswith("carlos solis")

    def test_rows_with_errors_are_left_out_and_counted(self, tenant):
        plan = plan_for(tenant, "Nombre,Apellido,Email", "Ana,Mora,a@x.org", "Beto,Solís,mal")
        counters = importer.apply_plan(plan, tenant, None)
        assert counters["created"] == 1 and counters["errors"] == 1
        assert not Member.objects.filter(first_name="Beto").exists()

    def test_a_failure_halfway_rolls_everything_back(self, tenant, monkeypatch):
        plan = plan_for(tenant, "Nombre,Apellido", "Ana,Mora", "Beto,Solís")
        real_save = Member.save
        calls = {"n": 0}

        def flaky(self, *a, **kw):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("disk full")
            return real_save(self, *a, **kw)

        monkeypatch.setattr(Member, "save", flaky)
        with pytest.raises(RuntimeError):
            importer.apply_plan(plan, tenant, None)
        assert Member.objects.filter(tenant=tenant).count() == 0

    def test_the_audit_trail_gets_one_summary_line_not_one_per_person(self, tenant, admin_user):
        before = AuditLog.objects.count()
        importer.apply_plan(
            plan_for(tenant, "Nombre,Apellido", "Ana,Mora", "Beto,Solís", "Carla,Rojas"), tenant, admin_user
        )
        new = list(AuditLog.objects.order_by("created_at")[before:])
        assert [e.action for e in new] == ["import"]
        assert "3 nuevos" in new[0].object_repr and new[0].user == admin_user

    def test_a_round_trip_through_our_own_export_reproduces_the_people(self, authenticated_client, tenant):
        family = Family.objects.create(tenant=tenant, name="Familia Mora")
        tag = Tag.objects.create(tenant=tenant, name="Alabanza")
        ana = Member.objects.create(
            tenant=tenant, first_name="Ana", last_name="Mora", email="ana@x.org", phone="+506 8888 1234",
            date_of_birth=date(1990, 5, 17), gender="female", marital_status="married", is_baptized=True,
            baptism_date=date(2010, 8, 1), member_status="member", family=family, city="Escazú",
        )
        ana.tags.add(tag)
        exported = authenticated_client.get(reverse("member_export")).content
        other = Tenant.objects.create(name="Destino", subdomain=f"dest-{uuid.uuid4().hex[:6]}")

        importer.apply_plan(importer.build_plan(exported, other), other, None)

        copy = Member.objects.get(tenant=other)
        for field in ("first_name", "last_name", "email", "phone", "date_of_birth", "gender",
                      "marital_status", "is_baptized", "baptism_date", "member_status", "city"):
            assert getattr(copy, field) == getattr(ana, field), field
        assert copy.family.name == "Familia Mora" and [t.name for t in copy.tags.all()] == ["Alabanza"]


@pytest.mark.django_db
class TestNotes:
    LINES = ("Nombre,Apellido,Notas", "Ana,Mora,visitar el jueves")

    def test_only_roles_that_may_see_notes_can_import_them(self, tenant):
        without = plan_for(tenant, *self.LINES, can_see_notes=False)
        assert "notes" not in without.rows[0].data
        assert any("Notas" in h for h in without.ignored_headers)
        assert plan_for(tenant, *self.LINES, can_see_notes=True).rows[0].data["notes"] == "visitar el jueves"


@pytest.mark.django_db
class TestScreens:
    URLS = ["member_import", "member_import_template"]

    def upload(self, client, content, name="gente.csv", policy="skip"):
        return client.post(
            reverse("member_import"),
            {"file": SimpleUploadedFile(name, content, content_type="text/csv"), "policy": policy},
        )

    @pytest.mark.parametrize("role", ["member", "treasurer", "teacher"])
    def test_roles_without_member_management_are_refused(self, role, tenant):
        client, _ = login_as(role, tenant)
        for name in self.URLS:
            assert client.get(reverse(name)).status_code == 403, name
        assert self.upload(client, csv_bytes("Nombre,Apellido", "Ana,Mora")).status_code == 403
        assert client.post(reverse("member_import_confirm"), {"token": "x"}).status_code == 403

    def test_anonymous_is_sent_to_login(self):
        assert Client().get(reverse("member_import")).status_code == 302

    @pytest.mark.parametrize("role", ["admin", "pastor", "volunteer"])
    def test_member_managers_can_open_it(self, role, tenant):
        client, _ = login_as(role, tenant)
        assert client.get(reverse("member_import")).status_code == 200

    def test_the_member_list_offers_the_import(self, authenticated_client):
        page = authenticated_client.get(reverse("member_list")).content.decode()
        assert reverse("member_import") in page

    def test_the_template_is_a_valid_importable_file(self, authenticated_client, tenant):
        response = authenticated_client.get(reverse("member_import_template"))
        text = response.content.decode("utf-8")
        assert text.startswith("﻿")
        rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
        assert rows[0][:2] == ["Nombre", "Apellido"] and len(rows) == 2
        plan = importer.build_plan(response.content, tenant)
        assert plan.rows[0].action == "create" and plan.ignored_headers == []

    def test_preview_saves_nothing_and_confirm_saves(self, authenticated_client, tenant):
        content = csv_bytes("Nombre,Apellido,Email", "Ana,Mora,ana@x.org", "Beto,Solís,mal-correo")

        preview = self.upload(authenticated_client, content)

        assert preview.status_code == 200
        assert preview.context["plan"].count_create == 1 and preview.context["plan"].count_error == 1
        assert "Correo no válido" in preview.content.decode()
        assert Member.objects.filter(tenant=tenant).count() == 0

        done = authenticated_client.post(
            reverse("member_import_confirm"), {"token": preview.context["token"]}, follow=True
        )

        assert "Importación lista: 1 nuevos" in done.content.decode()
        assert list(Member.objects.filter(tenant=tenant).values_list("first_name", flat=True)) == ["Ana"]

    def test_confirm_needs_the_token_from_this_session(self, authenticated_client, tenant):
        preview = self.upload(authenticated_client, csv_bytes("Nombre,Apellido", "Ana,Mora"))

        for token in ("", "otro", "../../etc/passwd"):
            response = authenticated_client.post(reverse("member_import_confirm"), {"token": token})
            assert response.status_code == 302 and response.url == reverse("member_import")
        assert Member.objects.filter(tenant=tenant).count() == 0
        # Someone else's session can't use the token either.
        client, _ = login_as("admin", tenant)
        response = client.post(reverse("member_import_confirm"), {"token": preview.context["token"]})
        assert response.url == reverse("member_import")
        assert Member.objects.filter(tenant=tenant).count() == 0

    def test_a_token_works_only_once(self, authenticated_client, tenant):
        token = self.upload(authenticated_client, csv_bytes("Nombre,Apellido", "Ana,Mora")).context["token"]
        authenticated_client.post(reverse("member_import_confirm"), {"token": token})
        authenticated_client.post(reverse("member_import_confirm"), {"token": token})
        assert Member.objects.filter(tenant=tenant).count() == 1

    def test_bad_files_show_the_reason_on_the_upload_page(self, authenticated_client):
        response = self.upload(authenticated_client, csv_bytes("Correo", "a@x.org"))
        assert response.status_code == 200
        assert "Faltan columnas obligatorias" in response.content.decode()
        assert self.upload(authenticated_client, b"").status_code == 200

    def test_no_file_at_all(self, authenticated_client):
        response = authenticated_client.post(reverse("member_import"), {})
        assert "Elige un archivo" in response.content.decode()

    def test_update_policy_is_honoured_end_to_end(self, authenticated_client, tenant):
        ana = Member.objects.create(tenant=tenant, first_name="Ana", last_name="Mora", email="ana@x.org")
        preview = self.upload(
            authenticated_client, csv_bytes("Nombre,Apellido,Email,Ciudad", "Ana,Mora,ana@x.org,Heredia"),
            policy="update",
        )
        assert preview.context["plan"].count_update == 1
        authenticated_client.post(reverse("member_import_confirm"), {"token": preview.context["token"]})
        ana.refresh_from_db()
        assert ana.city == "Heredia"

    def test_a_volunteer_cannot_smuggle_notes_in(self, tenant):
        client, _ = login_as("volunteer", tenant)
        preview = self.upload(client, csv_bytes("Nombre,Apellido,Notas", "Ana,Mora,secreto"))
        client.post(reverse("member_import_confirm"), {"token": preview.context["token"]})
        assert Member.objects.get(first_name="Ana").notes == ""
