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
        page.goto(f"{live_server_url}/onboarding/")

        # Fill church information
        page.fill("#id_name", "Iglesia Test E2E")
        page.fill("#id_subdomain", "iglesia-test-e2e")
        page.select_option("#id_country", "CR")
        page.select_option("#id_currency", "USD")

        # Submit form
        page.click("button[type='submit']")

        # Should navigate to step 2
        assert "/onboarding/" in page.url
        assert "Administrador" in page.content() or "admin" in page.url.lower()

    def test_onboarding_step2_admin_creation(self, page, live_server_url):
        """Test Step 2: Admin account creation."""
        # First complete step 1 (would need to handle this in real test)
        page.goto(f"{live_server_url}/onboarding/step-2/")

        # Fill admin information
        page.fill("#id_email", "admin@iglesiatest.com")
        page.fill("#id_first_name", "Admin")
        page.fill("#id_last_name", "Test")
        page.fill("#id_password1", "TestPassword123!")
        page.fill("#id_password2", "TestPassword123!")

        # Submit form
        page.click("button[type='submit']")

        # Should navigate to step 3 or dashboard
        assert page.url.endswith("/dashboard/") or "/onboarding/" in page.url

    def test_onboarding_navigation(self, page, live_server_url):
        """Test that all onboarding steps are accessible."""
        # Step 1
        page.goto(f"{live_server_url}/onboarding/")
        assert "Iglesia" in page.content() or "Registrar" in page.content()

        # Step 2
        page.goto(f"{live_server_url}/onboarding/step-2/")
        assert "admin" in page.content().lower() or "cuenta" in page.content().lower()

        # Step 3
        page.goto(f"{live_server_url}/onboarding/step-3/")
        assert (
            "configuración" in page.content().lower()
            or "settings" in page.content().lower()
        )


@pytest.mark.e2e
@pytest.mark.django_db
class TestAuthentication:
    """Test cases for authentication."""

    def test_login_success(self, page, live_server_url, admin_user):
        """Test successful login."""
        page.goto(f"{live_server_url}/accounts/login/")

        # Fill login form
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")

        # Submit
        page.click("button[type='submit']")

        # Should redirect to dashboard
        assert "/dashboard/" in page.url or "/accounts/" not in page.url

    def test_login_failure(self, page, live_server_url):
        """Test login with wrong credentials."""
        page.goto(f"{live_server_url}/accounts/login/")

        # Fill with wrong credentials
        page.fill("#id_email", "wrong@test.com")
        page.fill("#id_password", "wrongpassword")

        # Submit
        page.click("button[type='submit']")

        # Should show error
        assert (
            "error" in page.content().lower() or "incorrecto" in page.content().lower()
        )

    def test_logout(self, page, live_server_url, admin_user):
        """Test logout functionality."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to logout
        page.goto(f"{live_server_url}/accounts/logout/")

        # Should be logged out
        assert "/accounts/login/" in page.url or "login" in page.url.lower()
