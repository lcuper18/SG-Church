"""
E2E Tests: Onboarding Flow
Tests the complete church registration and onboarding process.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.django_db
class TestOnboarding:
    """Test cases for the onboarding flow."""

    def test_onboarding_step1_church_info(self, page, live_server_url):
        """Test Step 1: Church information form."""
        page.goto(f"{live_server_url}/onboarding/church/")

        page.fill("#name", "Iglesia Test E2E")
        page.select_option("#denomination", "evangelical")
        page.select_option("#country", "CR")
        page.fill("#city", "San José")

        page.click("button[type='submit']")

        # Step 1 stores data in the session and moves on to step 2 (admin)
        assert "/onboarding/admin/" in page.url
        assert "Administrador" in page.content()

    def test_onboarding_step2_admin_creation(self, page, live_server_url):
        """Test Step 2: Admin account creation (after completing step 1)."""
        page.goto(f"{live_server_url}/onboarding/church/")
        page.fill("#name", "Iglesia Test E2E")
        page.fill("#city", "San José")
        page.click("button[type='submit']")

        page.fill("#first_name", "Admin")
        page.fill("#last_name", "Test")
        page.fill("#email", "admin-step2@iglesiatest.com")
        page.fill("#password", "TestPassword123!")
        page.fill("#password_confirm", "TestPassword123!")
        page.check("#terms")

        page.click("button[type='submit']")

        # Step 2 stores data in the session and moves on to step 3 (settings)
        assert "/onboarding/settings/" in page.url

    def test_onboarding_full_flow_reaches_dashboard(self, page, live_server_url):
        """Completing all 3 steps creates the church/admin and lands on the
        dashboard - OnboardingCompleteView does the creation on GET and
        redirects straight there, it never actually renders complete.html."""
        page.goto(f"{live_server_url}/onboarding/church/")
        page.fill("#name", "Iglesia Test E2E Completa")
        page.select_option("#country", "CR")
        page.fill("#city", "San José")
        page.click("button[type='submit']")

        page.fill("#first_name", "Admin")
        page.fill("#last_name", "Test")
        page.fill("#email", "admin-full-flow@iglesiatest.com")
        page.fill("#password", "TestPassword123!")
        page.fill("#password_confirm", "TestPassword123!")
        page.check("#terms")
        page.click("button[type='submit']")

        page.select_option("#currency", "CRC")
        page.click("button[type='submit']")

        page.wait_for_url("**/dashboard/**")
        assert "/dashboard/" in page.url

    def test_onboarding_navigation(self, page, live_server_url):
        """Test that the onboarding start page and step 1 are directly
        accessible by URL. Steps 2/3 redirect back to step 1 if the
        previous step's session data isn't set yet (see
        OnboardingAdminView.get / OnboardingSettingsView.get), so those
        can't be visited directly without completing the prior steps."""
        page.goto(f"{live_server_url}/onboarding/")
        assert "Registrar" in page.content() or "Iglesia" in page.content()

        page.goto(f"{live_server_url}/onboarding/church/")
        assert "Iglesia" in page.content()


@pytest.mark.e2e
@pytest.mark.django_db
class TestAuthentication:
    """Test cases for authentication."""

    def test_login_success(self, page, live_server_url, admin_user):
        """Test successful login."""
        page.goto(f"{live_server_url}/accounts/login/")

        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")

        page.click("button[type='submit']")

        assert "/dashboard/" in page.url or "/accounts/" not in page.url

    def test_login_failure(self, page, live_server_url):
        """Test login with wrong credentials."""
        page.goto(f"{live_server_url}/accounts/login/")

        page.fill("#id_login", "wrong@test.com")
        page.fill("#id_password", "wrongpassword")

        page.click("button[type='submit']")

        assert "credenciales" in page.content().lower()

    def test_logout(self, page, live_server_url, admin_user):
        """Test logout functionality."""
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # allauth's logout view requires a POST confirmation - a bare GET
        # just shows the "are you sure?" page, it doesn't log out by itself.
        page.goto(f"{live_server_url}/accounts/logout/")
        page.click("button[type='submit']")

        # LOGOUT_REDIRECT_URL = "home" (see sg_church/settings/base.py), so
        # logout lands on the public home page, not the login page - confirm
        # the session was actually cleared via the nav showing "Iniciar
        # Sesión" again instead of a logged-in user menu.
        assert page.url == f"{live_server_url}/"
        assert "Iniciar Sesión" in page.content()
