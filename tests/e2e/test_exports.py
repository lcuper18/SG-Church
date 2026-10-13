"""
E2E Tests: the "Exportar CSV" buttons download real files.
"""

import pytest

from members.models import Member


@pytest.fixture
def two_members(admin_user):
    for first, status in (("Ana", "member"), ("Beto", "visitor")):
        Member.objects.create(
            tenant=admin_user.tenant, first_name=first, last_name="Demo", member_status=status
        )


@pytest.mark.e2e
@pytest.mark.django_db
class TestExportsE2E:
    def test_members_export_downloads_the_filtered_list(
        self, page, live_server_url, admin_user, two_members
    ):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/members/?status=visitor")
        with page.expect_download() as download_info:
            page.click("a:has-text('Exportar CSV')")
        download = download_info.value

        assert download.suggested_filename.startswith("miembros-")
        with open(download.path(), encoding="utf-8-sig") as handle:
            content = handle.read()
        assert "Beto" in content and "Ana" not in content
