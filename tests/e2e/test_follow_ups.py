"""
E2E Tests: recording a pastoral follow-up from a member's page and finishing it from the list.
"""

import pytest

PASSWORD = "testpassword123"


@pytest.fixture
def person(admin_user):
    from members.models import Member

    return Member.objects.create(tenant=admin_user.tenant, first_name="Ana", last_name="Pérez", member_status="visitor")


@pytest.mark.e2e
@pytest.mark.django_db
class TestFollowUpsE2E:
    def test_record_from_the_member_then_complete_from_the_list(self, person, page, live_server_url, admin_user):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/members/{person.pk}/")
        page.click("#followups-tab")
        page.select_option("#fu_kind", "visit")
        page.fill("#fu_notes", "Visitarla el sábado")
        page.click("#followup-form button[type='submit']")
        page.wait_for_url(lambda url: url.endswith("#followups"))
        assert "Seguimiento registrado" in page.content()
        assert "Visitarla el sábado" in page.content()

        page.goto(f"{live_server_url}/members/followups/")
        assert "Ana Pérez" in page.content() and "Visita" in page.content()
        page.click("button:has-text('Hecho')")
        page.wait_for_url(lambda url: "/followups/" in url)
        assert "No hay seguimiento con estos filtros" in page.content()
