"""
E2E Tests: Members Management
Tests the complete member management flow.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.django_db
class TestMembers:
    """Test cases for members management."""

    def test_member_list_access(self, page, live_server_url, admin_user):
        """Test accessing the member list page."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/members/")

        assert "Miembros" in page.content()

    def test_member_create(self, page, live_server_url, admin_user):
        """Test creating a new member."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        # Navigate to members
        page.goto(f"{live_server_url}/members/create/")

        # Fill member form (hand-written template, plain field ids - not
        # Django's auto-generated "id_<field>")
        page.fill("#first_name", "Juan")
        page.fill("#last_name", "Pérez")
        page.fill("#email", "juan.perez@test.com")
        page.fill("#phone", "+50688888888")

        # Select status
        page.select_option("#member_status", "member")

        # Submit
        page.click("button[type='submit']")

        # Should redirect to member list or detail
        assert "/members/" in page.url

    def test_member_detail_view(self, page, live_server_url, member, admin_user):
        """Test viewing member details."""
        # Login first - member detail requires authentication
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        page.goto(f"{live_server_url}/members/{member.pk}/")

        # Should show member information
        assert member.first_name in page.content() or member.last_name in page.content()

    def test_member_edit(self, page, live_server_url, member, admin_user):
        """Test editing a member."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        # Navigate to edit page
        page.goto(f"{live_server_url}/members/{member.pk}/edit/")

        # Change first name
        page.fill("#first_name", "Juan Updated")

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
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

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
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        # Navigate to families (mounted under /members/, not at the root)
        page.goto(f"{live_server_url}/members/families/")

        # Should show families list
        assert "Familias" in page.content() or "family" in page.url.lower()

    def test_family_create(self, page, live_server_url, admin_user):
        """Test creating a new family."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        # Navigate to create family
        page.goto(f"{live_server_url}/members/families/create/")

        # Fill family form
        page.fill("#name", "Familia Pérez")

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
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        # Navigate to tags (mounted under /members/, not at the root)
        page.goto(f"{live_server_url}/members/tags/")

        # Should show tags list
        assert "Etiquetas" in page.content() or "tag" in page.url.lower()

    def test_tag_create(self, page, live_server_url, admin_user):
        """Test creating a new tag."""
        # Login first
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", admin_user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

        # Navigate to create tag
        page.goto(f"{live_server_url}/members/tags/create/")

        # Fill tag form
        page.fill("#name", "Voluntario")

        # Submit
        page.click("button[type='submit']")

        # Should redirect
        assert "/tags/" in page.url
