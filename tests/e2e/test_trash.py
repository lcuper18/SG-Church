"""
E2E Tests: deleting sends a record to the trash, from where it can be restored,
and the audit trail shows who did it.
"""

import pytest

from members.models import Member

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.fixture
def sofia(admin_user):
    return Member.objects.create(tenant=admin_user.tenant, first_name="Sofía", last_name="Papelera")


@pytest.mark.e2e
@pytest.mark.django_db
class TestTrashE2E:
    def test_delete_restore_and_audit_trail(self, page, live_server_url, admin_user, sofia):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/members/{sofia.pk}/delete/")
        assert "papelera" in page.content().lower()
        page.click("button:has-text('Enviar a la papelera')")

        page.goto(f"{live_server_url}/members/")
        assert "Sofía Papelera" not in page.content()

        page.goto(f"{live_server_url}/trash/")
        assert "Sofía Papelera" in page.content()
        page.click("button:has-text('Restaurar')")
        assert "fue restaurado" in page.content()

        page.goto(f"{live_server_url}/members/")
        assert "Sofía Papelera" in page.content()

        page.goto(f"{live_server_url}/audit/")
        content = page.content()
        assert "Envió a la papelera" in content and "Restauró" in content
        assert admin_user.email in content
