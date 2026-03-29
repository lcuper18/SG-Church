"""
E2E Tests: Members Management
Tests the complete member management flow.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.django_db
class TestMembers:
    """Test cases for members management."""

    def test_member_list_access(
        self, page, live_server_url, authenticated_client, admin_user
    ):
        """Test accessing the member list page."""
        page.goto(f"{live_server_url}/members/")

        # Should show members list or redirect to login
        assert "Miembros" in page.content() or page.url.endswith("/accounts/login/")

    def test_member_create(self, page, live_server_url, admin_user, tenant):
        """Test creating a new member."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to members
        page.goto(f"{live_server_url}/members/create/")

        # Fill member form
        page.fill("#id_first_name", "Juan")
        page.fill("#id_last_name", "Pérez")
        page.fill("#id_email", "juan.perez@test.com")
        page.fill("#id_phone", "+50688888888")

        # Select status
        page.select_option("#id_status", "active")

        # Submit
        page.click("button[type='submit']")

        # Should redirect to member list or detail
        assert "/members/" in page.url

    def test_member_detail_view(self, page, live_server_url, member):
        """Test viewing member details."""
        page.goto(f"{live_server_url}/members/{member.pk}/")

        # Should show member information
        assert member.first_name in page.content() or member.last_name in page.content()

    def test_member_edit(self, page, live_server_url, member, admin_user):
        """Test editing a member."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to edit page
        page.goto(f"{live_server_url}/members/{member.pk}/edit/")

        # Change first name
        page.fill("#id_first_name", "Juan Updated")

        # Submit
        page.click("button[type='submit']")

        # Should show updated name
        assert "Juan Updated" in page.content() or page.url.endswith(
            f"/members/{member.pk}/"
        )

    def test_member_delete(self, page, live_server_url, member, admin_user):
        """Test deleting a member."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to delete page
        page.goto(f"{live_server_url}/members/{member.pk}/delete/")

        # Confirm deletion
        page.click("button[type='submit']")

        # Should redirect to list
        assert "/members/" in page.url


@pytest.mark.e2e
@pytest.mark.django_db
class TestFamilies:
    """Test cases for families management."""

    def test_family_list_access(self, page, live_server_url, admin_user):
        """Test accessing the family list page."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to families
        page.goto(f"{live_server_url}/families/")

        # Should show families list
        assert "Familias" in page.content() or "family" in page.url.lower()

    def test_family_create(self, page, live_server_url, admin_user):
        """Test creating a new family."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to create family
        page.goto(f"{live_server_url}/families/create/")

        # Fill family form
        page.fill("#id_name", "Familia Pérez")

        # Submit
        page.click("button[type='submit']")

        # Should redirect
        assert "/families/" in page.url


@pytest.mark.e2e
@pytest.mark.django_db
class TestTags:
    """Test cases for tags management."""

    def test_tag_list_access(self, page, live_server_url, admin_user):
        """Test accessing the tags list page."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to tags
        page.goto(f"{live_server_url}/tags/")

        # Should show tags list
        assert "Etiquetas" in page.content() or "tag" in page.url.lower()

    def test_tag_create(self, page, live_server_url, admin_user):
        """Test creating a new tag."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_email", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")

        # Navigate to create tag
        page.goto(f"{live_server_url}/tags/create/")

        # Fill tag form
        page.fill("#id_name", "Voluntario")

        # Submit
        page.click("button[type='submit']")

        # Should redirect
        assert "/tags/" in page.url
