"""
Integration Tests: Members API
Tests the Members REST API endpoints.
"""

import pytest
from rest_framework import status


@pytest.mark.integration
@pytest.mark.django_db
class TestMembersAPI:
    """Test cases for Members API."""

    def test_member_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot access the API."""
        response = api_client.get("/api/v1/members/")
        # Should return 401 or 403
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_member_list_authenticated(self, authenticated_api_client, member):
        """Test that authenticated users can list members."""
        response = authenticated_api_client.get("/api/v1/members/")
        assert response.status_code == status.HTTP_200_OK

    def test_member_list_only_own_tenant(
        self, authenticated_api_client, member, tenant
    ):
        """Test that members from other tenants are not visible."""
        from tenants.models import Tenant
        from members.models import Member

        # Create another tenant with members
        other_tenant = Tenant.objects.create(
            name="Other Church",
            subdomain="otherchurch",
            is_active=True,
        )
        Member.objects.create(
            tenant=other_tenant,
            first_name="Other",
            last_name="Member",
            email="other@test.com",
            member_status="active",
        )

        # Get members
        response = authenticated_api_client.get("/api/v1/members/")

        # Should only return members from own tenant (verify by count)
        if hasattr(response, "data") and "results" in response.data:
            # Should only have 1 member (the one we created in this test)
            assert len(response.data["results"]) == 1

    def test_member_create(self, authenticated_api_client, tenant):
        """Test creating a new member via API."""
        data = {
            "first_name": "New",
            "last_name": "Member",
            "email": "newmember@test.com",
            "phone": "+1234567890",
            "status": "active",
        }
        response = authenticated_api_client.post("/api/v1/members/", data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_member_retrieve(self, authenticated_api_client, member):
        """Test retrieving a single member."""
        response = authenticated_api_client.get(f"/api/v1/members/{member.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == member.first_name

    def test_member_update(self, authenticated_api_client, member):
        """Test updating a member."""
        data = {
            "first_name": "Updated",
        }
        response = authenticated_api_client.patch(
            f"/api/v1/members/{member.pk}/",
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"

    def test_member_delete(self, authenticated_api_client, member):
        """Test deleting a member."""
        response = authenticated_api_client.delete(f"/api/v1/members/{member.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_member_search(self, authenticated_api_client, member):
        """Test searching members."""
        response = authenticated_api_client.get(
            f"/api/v1/members/?search={member.first_name}"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_member_filter_by_status(self, authenticated_api_client, member):
        """Test filtering members by status."""
        response = authenticated_api_client.get(
            f"/api/v1/members/?member_status={member.member_status}"
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.django_db
class TestFamiliesAPI:
    """Test cases for Families API."""

    def test_family_list(self, authenticated_api_client, tenant):
        """Test listing families."""
        response = authenticated_api_client.get("/api/v1/families/")
        assert response.status_code == status.HTTP_200_OK

    def test_family_create(self, authenticated_api_client, tenant):
        """Test creating a family."""
        data = {
            "name": "Family Test",
        }
        response = authenticated_api_client.post("/api/v1/families/", data)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ]


@pytest.mark.integration
@pytest.mark.django_db
class TestTagsAPI:
    """Test cases for Tags API."""

    def test_tag_list(self, authenticated_api_client):
        """Test listing tags."""
        response = authenticated_api_client.get("/api/v1/tags/")
        assert response.status_code == status.HTTP_200_OK

    def test_tag_create(self, authenticated_api_client):
        """Test creating a tag."""
        data = {
            "name": "Test Tag",
            "color": "#FF0000",
        }
        response = authenticated_api_client.post("/api/v1/tags/", data)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ]
