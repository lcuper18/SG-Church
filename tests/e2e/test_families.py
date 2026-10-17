"""
E2E Tests: choosing a family's members from the family form and seeing them on
the family page.
"""

import pytest

from members.models import Family, Member


@pytest.fixture
def family_and_people(admin_user):
    tenant = admin_user.tenant
    family = Family.objects.create(tenant=tenant, name="Familia Mora")
    for first in ("Ana", "Beto", "Carla"):
        Member.objects.create(tenant=tenant, first_name=first, last_name="Mora")
    return family


@pytest.mark.e2e
@pytest.mark.django_db
class TestFamilyMembersE2E:
    def _login(self, page, live_server_url, user):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

    def _pick(self, page, text):
        """Search, wait for the one match and click it."""
        page.fill("#member-filter", text)
        page.wait_for_function(
            "document.querySelectorAll('.member-pick').length === 1"
            " && !document.querySelector('.member-pick.disabled')"
        )
        page.click(".member-pick")

    def test_pick_members_with_the_search_and_see_them_on_the_family_page(
        self, page, live_server_url, admin_user, family_and_people
    ):
        family = family_and_people
        self._login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/members/families/{family.pk}/edit/")
        self._pick(page, "carla")
        assert page.inner_text("#selected-count") == "1"

        self._pick(page, "ana")
        page.click("button:has-text('Guardar Cambios')")

        assert page.url.rstrip("/").endswith(str(family.pk))
        body = page.inner_text("body")
        assert "Carla Mora" in body and "Ana Mora" in body and "Beto Mora" not in body

    def test_enter_in_the_search_box_does_not_submit_the_form(
        self, page, live_server_url, admin_user, family_and_people
    ):
        family = family_and_people
        self._login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/members/families/{family.pk}/edit/")
        page.fill("#member-filter", "beto")
        page.wait_for_function("document.querySelectorAll('.member-pick').length === 1")
        page.press("#member-filter", "Enter")

        # Enter picks the single match instead of submitting the form.
        page.wait_for_selector(".member-chip")
        assert "/edit/" in page.url

    def test_create_a_family_with_members(
        self, page, live_server_url, admin_user, family_and_people
    ):
        self._login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/members/families/create/")
        page.fill("#name", "Familia Nueva")
        self._pick(page, "beto")
        page.click("button:has-text('Crear Familia')")

        assert "Familia Nueva" in page.inner_text("body")
        assert "Beto Mora" in page.inner_text("table.table-hover")
