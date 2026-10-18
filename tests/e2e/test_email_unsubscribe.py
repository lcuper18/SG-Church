"""
E2E Tests: the unsubscribe link in an e-mail, opened by someone who is not logged in.
"""

import pytest


@pytest.fixture
def link(admin_user):
    from emails.unsubscribe import make_token
    from members.models import Member

    member = Member.objects.create(
        tenant=admin_user.tenant, first_name="Ana", last_name="Pérez", email="ana@iglesia.org"
    )
    return f"/email/unsubscribe/{make_token(member)}/", member.pk


@pytest.mark.e2e
@pytest.mark.django_db
class TestUnsubscribeE2E:
    def test_unsubscribe_then_change_your_mind(self, link, page, live_server_url):
        path, _ = link
        page.goto(f"{live_server_url}{path}")
        page.click("button:has-text('Dejar de recibir recordatorios y anuncios')")
        assert "Ya no recibirás" in page.content()
        page.goto(f"{live_server_url}{path}")
        assert "Ya no recibes estos avisos" in page.content()
        page.click("button:has-text('Volver a recibirlos')")
        assert "Volverás a recibirlos" in page.content()
        page.goto(f"{live_server_url}{path}")
        assert "¿Dejar de recibir avisos?" in page.content()
        page.click("button:has-text('Dejar de recibir recordatorios y anuncios')")

        page.click("button:has-text('Me equivoqué')")
        assert "Volverás a recibirlos" in page.content()
