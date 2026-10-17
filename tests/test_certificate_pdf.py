"""
Block certificates as PDF: content, who may download them, the public check
page, and the church's signature settings.
"""

import io
import uuid

import pytest
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader

from education.certificates import long_date, render_certificate_pdf
from education.models import BlockCertificate, Course, CourseBlock, Enrollment
from members.models import Member, User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"


def login_as(role, tenant, **kwargs):
    user = User.objects.create_user(
        email=f"{role}-{uuid.uuid4().hex[:6]}@t.com", password=STRONG, role=role, tenant=tenant, **kwargs
    )
    client = Client()
    client.force_login(user)
    return client, user


def make_certificate(tenant, first="Lucía", last="Fernández", block_name="Discipulado", titles=("Fe", "Oración")):
    member = Member.objects.create(tenant=tenant, first_name=first, last_name=last)
    block = CourseBlock.objects.create(tenant=tenant, name=block_name)
    for index, title in enumerate(titles):
        course = Course.objects.create(tenant=tenant, title=title, course_block=block, order_in_block=index)
        Enrollment.objects.create(tenant=tenant, member=member, course=course).mark_completed()
    return member.block_certificates.get(course_block=block)


def text_of(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    return reader.pages[0].extract_text()


@pytest.fixture
def tenant(admin_user):
    return admin_user.tenant


@pytest.mark.django_db
class TestPdfContent:
    def test_carries_everything_printed_on_the_certificate(self, tenant):
        tenant.name = "Iglesia Oasis de Vida"
        tenant.certificate_signer_name = "Pastor Luis Fallas"
        tenant.certificate_signer_title = "Pastor principal"
        tenant.save()
        certificate = make_certificate(tenant)

        pdf = render_certificate_pdf(certificate, "https://x.example/v/CERT/")
        assert pdf.startswith(b"%PDF")
        text = text_of(pdf)

        for expected in ("Iglesia Oasis de Vida", "Lucía Fernández", "Discipulado", "Fe", "Oración",
                         "Pastor Luis Fallas", "Pastor principal", certificate.certificate_number,
                         "https://x.example/v/CERT/", "Fecha de emisión"):
            assert expected in text, expected

    def test_dates_are_written_in_spanish(self):
        from datetime import date

        assert long_date(date(2026, 10, 17)) == "17 de octubre de 2026"
        assert long_date(date(2027, 1, 1)) == "1 de enero de 2027"

    def test_without_a_signer_it_still_has_a_signature_line(self, tenant):
        tenant.certificate_signer_name = ""
        tenant.certificate_signer_title = ""
        tenant.save()
        assert "Firma autorizada" in text_of(render_certificate_pdf(make_certificate(tenant)))

    def test_very_long_and_unusual_names_do_not_break_it(self, tenant):
        certificate = make_certificate(
            tenant, first="María de los Ángeles Guadalupe", last="Rodríguez Fernández-Quesada de la Vega " * 2,
            block_name="Formación de Líderes: Discipulado, Servicio y Misiones en la Comunidad Local " * 2,
            titles=tuple(f"Curso número {i} con un título bastante largo" for i in range(12)),
        )
        assert text_of(render_certificate_pdf(certificate, "https://x.example/v/")).strip()

    def test_characters_the_pdf_fonts_lack_become_question_marks(self, tenant):
        certificate = make_certificate(tenant, first="Łukasz", last="Żółć")
        text = text_of(render_certificate_pdf(certificate))
        assert "?ukasz" in text  # not a crash, not an invisible box

    def test_the_church_logo_is_included_when_there_is_one(self, tenant):
        certificate = make_certificate(tenant)
        assert len(PdfReader(io.BytesIO(render_certificate_pdf(certificate))).pages[0].images) == 0

        picture = io.BytesIO()
        Image.new("RGB", (300, 120), (31, 58, 95)).save(picture, "PNG")
        tenant.logo.save("logo.png", ContentFile(picture.getvalue()), save=True)
        certificate.refresh_from_db()

        assert len(PdfReader(io.BytesIO(render_certificate_pdf(certificate))).pages[0].images) == 1

    def test_an_unreadable_logo_is_skipped(self, tenant):
        certificate = make_certificate(tenant)
        tenant.logo.name = "church_logos/missing.png"
        tenant.save()
        certificate.refresh_from_db()
        assert text_of(render_certificate_pdf(certificate))


@pytest.mark.django_db
class TestDownload:
    def url(self, certificate):
        return reverse("block_certificate_pdf", args=[certificate.pk])

    def test_staff_download_a_named_pdf(self, authenticated_client, tenant):
        certificate = make_certificate(tenant, block_name="Formación de Líderes")

        response = authenticated_client.get(self.url(certificate))

        assert response.status_code == 200 and response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"] == (
            'attachment; filename="certificado-formacion-de-lideres-lucia-fernandez.pdf"'
        )
        assert response.content.startswith(b"%PDF")
        # The QR/URL points at the public check page.
        assert f"/education/certificates/verify/{certificate.certificate_number}/" in text_of(response.content)

    def test_inline_view_for_the_browser_viewer(self, authenticated_client, tenant):
        certificate = make_certificate(tenant)
        response = authenticated_client.get(self.url(certificate), {"inline": "1"})
        assert response["Content-Disposition"].startswith("inline;")

    def test_owner_can_download_theirs_but_not_others(self, tenant):
        mine, other = make_certificate(tenant), make_certificate(tenant, first="Otra", last="Persona", block_name="B2")
        client, _ = login_as("member", tenant, member_profile=mine.member)

        assert client.get(self.url(mine)).status_code == 200
        assert client.get(self.url(other)).status_code == 404

    def test_anonymous_is_sent_to_login_and_other_churches_get_404(self, authenticated_client, tenant):
        certificate = make_certificate(tenant)
        assert Client().get(self.url(certificate)).status_code == 302
        other = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
        client, _ = login_as("admin", other)
        assert client.get(self.url(certificate)).status_code == 404

    def test_the_printable_page_offers_the_download(self, authenticated_client, tenant):
        certificate = make_certificate(tenant)
        page = authenticated_client.get(reverse("block_certificate_detail", args=[certificate.pk])).content.decode()
        assert self.url(certificate) in page and "Descargar PDF" in page


@pytest.mark.django_db
class TestVerification:
    def test_anyone_can_check_a_real_certificate_without_logging_in(self, tenant):
        certificate = make_certificate(tenant)

        response = Client().get(reverse("certificate_verify", args=[certificate.certificate_number]))

        page = response.content.decode()
        assert response.status_code == 200
        assert "Certificado auténtico" in page and "Lucía Fernández" in page and "Discipulado" in page

    def test_the_number_is_case_insensitive(self, tenant):
        certificate = make_certificate(tenant)
        response = Client().get(reverse("certificate_verify", args=[certificate.certificate_number.lower()]))
        assert response.status_code == 200

    def test_unknown_numbers_say_so(self):
        response = Client().get(reverse("certificate_verify", args=["CERT-2026-NOEXISTE"]))
        assert response.status_code == 404
        assert "Certificado no encontrado" in response.content.decode()

    def test_a_trashed_person_no_longer_verifies(self, tenant):
        certificate = make_certificate(tenant)
        certificate.member.delete()
        assert Client().get(reverse("certificate_verify", args=[certificate.certificate_number])).status_code == 404

    def test_reveals_nothing_beyond_the_printed_certificate(self, tenant):
        certificate = make_certificate(tenant)
        certificate.member.email = "privado@ejemplo.org"
        certificate.member.phone = "555-0199"
        certificate.member.save()
        page = Client().get(reverse("certificate_verify", args=[certificate.certificate_number])).content.decode()
        assert "privado@ejemplo.org" not in page and "555-0199" not in page


@pytest.mark.django_db
class TestSignatureSettings:
    def test_admin_sets_who_signs(self, authenticated_client, tenant):
        response = authenticated_client.post(
            reverse("church_settings"),
            {
                "name": tenant.name, "denomination": "", "country": "CR", "city": "", "state": "",
                "address": "", "phone": "", "email": "", "currency": tenant.currency,
                "timezone": tenant.timezone, "enable_families": "on", "enable_tags": "on",
                "certificate_signer_name": "Pastor Luis Fallas", "certificate_signer_title": "Pastor principal",
            },
        )
        assert response.status_code == 302
        tenant.refresh_from_db()
        assert (tenant.certificate_signer_name, tenant.certificate_signer_title) == (
            "Pastor Luis Fallas", "Pastor principal",
        )

    def test_the_settings_page_shows_the_fields(self, authenticated_client):
        page = authenticated_client.get(reverse("church_settings")).content.decode()
        assert 'name="certificate_signer_name"' in page and "Cargo de quien firma" in page
