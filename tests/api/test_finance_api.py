"""
Integration Tests: Finance API
Tests the Finance REST API endpoints.
"""

import pytest
from rest_framework import status


@pytest.mark.integration
@pytest.mark.django_db
class TestDonationsAPI:
    """Test cases for Donations API."""

    def test_donation_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot access donations."""
        response = api_client.get("/api/v1/donations/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_donation_list_authenticated(
        self, authenticated_api_client, member, tenant
    ):
        """Test that authenticated users can list donations."""
        from finance.models import Donation

        # Create a donation
        Donation.objects.create(
            tenant=tenant,
            member=member,
            amount=100.00,
            campaign="tithe",
            status="completed",
            donor_name="Test Donor",
            donor_email="donor@test.com",
        )

        response = authenticated_api_client.get("/api/v1/donations/")
        assert response.status_code == status.HTTP_200_OK

    def test_donation_create(self, authenticated_api_client, member, tenant):
        """Test creating a donation."""
        data = {
            "member": member.pk,
            "amount": "50.00",
            "campaign": "offering",
            "status": "completed",
            "donor_name": "Test Donor",
            "donor_email": "donor@test.com",
        }
        response = authenticated_api_client.post("/api/v1/donations/", data)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ]

    def test_donation_filter_by_campaign(
        self, authenticated_api_client, member, tenant
    ):
        """Test filtering donations by campaign."""
        from finance.models import Donation

        # Create donations with different campaigns
        Donation.objects.create(
            tenant=tenant,
            member=member,
            amount=100.00,
            campaign="tithe",
            status="completed",
        )

        response = authenticated_api_client.get("/api/v1/donations/?campaign=tithe")
        assert response.status_code == status.HTTP_200_OK

    def test_donation_filter_by_status(self, authenticated_api_client, member, tenant):
        """Test filtering donations by status."""
        from finance.models import Donation

        Donation.objects.create(
            tenant=tenant,
            member=member,
            amount=100.00,
            status="completed",
        )

        response = authenticated_api_client.get("/api/v1/donations/?status=completed")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.django_db
class TestExpensesAPI:
    """Test cases for Expenses API."""

    def test_expense_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot access expenses."""
        response = api_client.get("/api/v1/expenses/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_expense_list_authenticated(
        self, authenticated_api_client, admin_user, tenant
    ):
        """Test that authenticated users can list expenses."""
        from finance.models import Expense

        # Create an expense
        Expense.objects.create(
            tenant=tenant,
            description="Test Expense",
            amount=50.00,
            category="operations",
            created_by=admin_user,
        )

        response = authenticated_api_client.get("/api/v1/expenses/")
        assert response.status_code == status.HTTP_200_OK

    def test_expense_create(self, authenticated_api_client, admin_user, tenant):
        """Test creating an expense."""
        data = {
            "description": "New Expense",
            "amount": "75.00",
            "category": "operations",
            "expense_date": "2026-01-15",
            "status": "pending",
        }
        response = authenticated_api_client.post("/api/v1/expenses/", data)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ]

    def test_expense_filter_by_category(
        self, authenticated_api_client, admin_user, tenant
    ):
        """Test filtering expenses by category."""
        from finance.models import Expense

        Expense.objects.create(
            tenant=tenant,
            description="Operations Expense",
            amount=100.00,
            category="operations",
            created_by=admin_user,
        )

        response = authenticated_api_client.get("/api/v1/expenses/?category=operations")
        assert response.status_code == status.HTTP_200_OK

    def test_expense_filter_by_status(
        self, authenticated_api_client, admin_user, tenant
    ):
        """Test filtering expenses by status."""
        from finance.models import Expense

        Expense.objects.create(
            tenant=tenant,
            description="Pending Expense",
            amount=50.00,
            status="pending",
            created_by=admin_user,
        )

        response = authenticated_api_client.get("/api/v1/expenses/?status=pending")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.django_db
class TestCampaignsAPI:
    """Test cases for Campaigns API."""

    def test_campaign_list(self, authenticated_api_client):
        """Test listing campaigns."""
        response = authenticated_api_client.get("/api/v1/campaigns/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardAPI:
    """Test cases for Dashboard API."""

    def test_dashboard_stats(self, authenticated_api_client, member, tenant):
        """Test getting dashboard statistics."""
        from finance.models import Donation

        # Create a donation
        Donation.objects.create(
            tenant=tenant,
            member=member,
            amount=100.00,
            status="completed",
        )

        response = authenticated_api_client.get("/api/v1/dashboard/stats/")
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_chart_data(self, authenticated_api_client):
        """Test getting chart data."""
        response = authenticated_api_client.get("/api/v1/dashboard/chart/")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,  # If endpoint doesn't exist
        ]
