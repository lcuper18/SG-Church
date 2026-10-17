"""
E2E Tests: what a plain church member sees, and how an administrator links a
login to a member record.
"""

import pytest

from education.models import Course, Enrollment
from members.models import Member, User

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.fixture
def onboarded(admin_user):
    admin_user.tenant.onboarding_completed = True
    admin_user.tenant.save()
    return admin_user.tenant


@pytest.fixture
def lucia(onboarded):
    return Member.objects.create(
        tenant=onboarded, first_name="Lucía", last_name="Portal", email="lucia@e2e.test",
        phone="555-0000", notes="Nota privada de Lucía",
    )


@pytest.fixture
def lucia_login(onboarded, lucia):
    course = Course.objects.create(tenant=onboarded, title="Fundamentos de Fe")
    Enrollment.objects.create(tenant=onboarded, member=lucia, course=course)
    return User.objects.create_user(
        email="lucia@e2e.test", password=PASSWORD, first_name="Lucía", last_name="Portal",
        role="member", tenant=onboarded, member_profile=lucia,
    )


@pytest.fixture
def free_member(onboarded):
    return Member.objects.create(tenant=onboarded, first_name="Pedro", last_name="Sinlogin")


@pytest.mark.e2e
@pytest.mark.django_db
class TestMemberPortalE2E:
    def test_a_plain_member_sees_their_record_and_no_directory(
        self, page, live_server_url, lucia_login
    ):
        _login(page, live_server_url, lucia_login)

        # The dashboard offers no directory or finance menus...
        page.goto(f"{live_server_url}/dashboard/")
        content = page.content()
        assert "Comunidad" not in content and "Finanzas" not in content
        assert "Total Miembros" not in content

        # ...and the directory itself is closed.
        assert page.goto(f"{live_server_url}/members/").status == 403

        page.goto(f"{live_server_url}/me/")
        assert "Lucía Portal" in page.content()
        assert "Fundamentos de Fe" in page.content()
        assert "Nota privada" not in page.content()

    def test_member_updates_their_phone(self, page, live_server_url, lucia_login):
        _login(page, live_server_url, lucia_login)

        page.goto(f"{live_server_url}/me/")
        page.click("a:has-text('Actualizar mis datos de contacto')")
        page.fill("#phone", "555-1234")
        page.click("button:has-text('Guardar')")

        assert "Tus datos de contacto se actualizaron" in page.content()
        assert "555-1234" in page.content()

    def test_admin_links_a_login_to_a_member_record(
        self, page, live_server_url, admin_user, free_member
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/users/create/")
        page.fill("#id_first_name", "Pedro")
        page.fill("#id_last_name", "Sinlogin")
        page.fill("#id_email", "pedro@e2e.test")
        page.select_option("#id_role", "member")
        page.select_option("#id_member_profile", label="Pedro Sinlogin")
        page.fill("#id_password1", "Clave-Segura-2026")
        page.fill("#id_password2", "Clave-Segura-2026")
        page.click("button:has-text('Crear usuario')")

        assert page.url.rstrip("/").endswith("/users")
        assert "pedro@e2e.test" in page.content()
