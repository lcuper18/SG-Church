"""
E2E Tests: downloading a block certificate as PDF and checking it publicly.
"""

import pytest

from education.models import Course, CourseBlock, Enrollment
from members.models import Member

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.fixture
def certificate(admin_user):
    tenant = admin_user.tenant
    member = Member.objects.create(tenant=tenant, first_name="Rebeca", last_name="Diploma")
    block = CourseBlock.objects.create(tenant=tenant, name="Discipulado")
    course = Course.objects.create(tenant=tenant, title="Fundamentos", course_block=block)
    Enrollment.objects.create(tenant=tenant, member=member, course=course).mark_completed()
    return member.block_certificates.get()


@pytest.mark.e2e
@pytest.mark.django_db
class TestCertificatePdfE2E:
    def test_download_the_pdf_and_check_it_without_logging_in(
        self, page, live_server_url, admin_user, certificate
    ):
        _login(page, live_server_url, admin_user)
        page.goto(f"{live_server_url}/education/certificates/{certificate.pk}/")

        with page.expect_download() as download:
            page.click("a:has-text('Descargar PDF')")

        assert download.value.suggested_filename == "certificado-discipulado-rebeca-diploma.pdf"
        with open(download.value.path(), "rb") as handle:
            assert handle.read(5) == b"%PDF-"

        # The number printed on it opens the public check page, no login needed.
        page.context.clear_cookies()
        page.goto(f"{live_server_url}/education/certificates/verify/{certificate.certificate_number}/")
        assert "Certificado auténtico" in page.content()
        assert "Rebeca Diploma" in page.content()
