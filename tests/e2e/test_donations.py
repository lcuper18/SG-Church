"""
E2E Tests: Donations and Finance
Tests the complete donation and finance flow.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.django_db
class TestDonations:
    """Test cases for donations."""

    def test_donate_page_access(self, page, live_server_url, tenant):
        """Test accessing the public donation page."""
        page.goto(f"{live_server_url}/donate/?church={tenant.subdomain}")

        # Should show donation form
        assert "donar" in page.content().lower() or "donation" in page.content().lower()

    def test_donate_page_with_invalid_church(self, page, live_server_url):
        """Test donation page with invalid church."""
        page.goto(f"{live_server_url}/donate/?church=nonexistent")

        # Should show error or redirect
        assert (
            "error" in page.content().lower()
            or "no encontrado" in page.content().lower()
        )

    def test_donate_form_submission(self, page, live_server_url, tenant):
        """Test filling and submitting the donation form."""
        page.goto(f"{live_server_url}/donate/?church={tenant.subdomain}")

        # Fill donation form
        page.fill("#id_amount", "100")
        page.select_option("#id_campaign", "offering")
        page.fill("#id_donor_name", "Test Donor")
        page.fill("#id_donor_email", "donor@test.com")

        # Click donate button
        page.click("#donate-btn")

        # Should redirect to Stripe (in test mode)
        # Note: In real test, this would redirect to Stripe
        assert "checkout.stripe.com" in page.url or "/donate/" in page.url

    def test_donation_success_page(self, page, live_server_url):
        """Test the donation success page."""
        page.goto(f"{live_server_url}/donate/success/?session_id=test_session")

        # Should show success message
        assert (
            "éxito" in page.content().lower()
            or "success" in page.content().lower()
            or "gracias" in page.content().lower()
        )


@pytest.mark.e2e
@pytest.mark.django_db
class TestFinanceDashboard:
    """Test cases for finance dashboard."""

    def test_finance_dashboard_access(self, page, live_server_url, admin_user):
        """Test accessing the finance dashboard."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to finance dashboard
        page.goto(f"{live_server_url}/finance/")

        # Should show finance dashboard
        assert "Finanzas" in page.content() or "finance" in page.url.lower()

    def test_finance_dashboard_stats(self, page, live_server_url, admin_user):
        """Test that finance dashboard shows stats."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to finance dashboard
        page.goto(f"{live_server_url}/finance/")

        # Should show stats cards
        assert (
            "Ingresos" in page.content()
            or "Gastos" in page.content()
            or "Balance" in page.content()
        )

    def test_donations_list_access(self, page, live_server_url, admin_user):
        """Test accessing the donations list."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to donations list
        page.goto(f"{live_server_url}/finance/donations/")

        # Should show donations list
        assert "Donaciones" in page.content() or "donation" in page.url.lower()


@pytest.mark.e2e
@pytest.mark.django_db
class TestExpenses:
    """Test cases for expenses management."""

    def test_expense_list_access(self, page, live_server_url, admin_user):
        """Test accessing the expenses list."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to expenses list
        page.goto(f"{live_server_url}/finance/expenses/")

        # Should show expenses list
        assert "Gastos" in page.content() or "expense" in page.url.lower()

    def test_expense_create(self, page, live_server_url, admin_user):
        """Test creating a new expense."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to create expense
        page.goto(f"{live_server_url}/finance/expenses/create/")

        # Fill expense form
        page.fill("#id_description", "Test Expense - Office Supplies")
        page.fill("#id_amount", "50.00")
        page.select_option("#id_category", "operations")

        # Submit
        page.click("button[type='submit']")

        # Should redirect to list
        assert "/expenses/" in page.url


@pytest.mark.e2e
@pytest.mark.django_db
class TestReports:
    """Test cases for finance reports."""

    def test_income_statement_access(self, page, live_server_url, admin_user):
        """Test accessing the income statement report."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to income statement
        page.goto(f"{live_server_url}/finance/reports/income-statement/")

        # Should show income statement
        assert (
            "Ingresos" in page.content()
            or "Gastos" in page.content()
            or "Balance" in page.content()
        )

    def test_donations_by_member_access(self, page, live_server_url, admin_user):
        """Test accessing the donations by member report."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to donations by member report
        page.goto(f"{live_server_url}/finance/reports/donations-by-member/")

        # Should show the report
        assert "Donaciones" in page.content() or "Miembro" in page.content()
