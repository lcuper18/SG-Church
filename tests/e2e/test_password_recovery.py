"""
E2E Tests: the administrator gives a reset link to someone who forgot their password.
"""

import pytest

PASSWORD = "testpassword123"
NEW = "Clave-Nueva-2027-xyz"


@pytest.fixture
def colleague(admin_user):
    from members.models import User

    return User.objects.create_user(
        email="olvidadiza@iglesia.org", password="Clave-Antigua-2026", role="pastor",
        tenant=admin_user.tenant, first_name="Olga", last_name="Olvidadiza",
    )


@pytest.mark.e2e
@pytest.mark.django_db
class TestPasswordRecoveryE2E:
    def test_admin_generates_a_link_and_the_person_sets_a_new_password(
        self, colleague, page, live_server_url, admin_user
    ):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/users/")
        page.click("button[aria-label*='Olga Olvidadiza'][title*='restablecer']")
        page.wait_for_selector("#reset-url")
        link = page.input_value("#reset-url")
        assert "/accounts/password/reset/key/" in link

        # The person opens it in their own browser, not the administrator's.
        other = page.context.browser.new_context()
        try:
            person = other.new_page()
            person.goto(link)
            person.fill("input[name='password1']", NEW)
            person.fill("input[name='password2']", NEW)
            person.click("button[type='submit']")
            person.wait_for_load_state()
            person.goto(f"{live_server_url}/accounts/login/")
            person.fill("#id_login", colleague.email)
            person.fill("#id_password", NEW)
            person.click("button[type='submit']")
            person.wait_for_url(lambda url: "/accounts/login/" not in url)
        finally:
            other.close()
