"""
Pytest configuration and fixtures for SG Church tests.
"""

import os
import pytest
import django
from django.conf import settings


# Configure Django settings before importing Django models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sg_church.settings.test")


def pytest_configure(config):
    """Configure Django settings for pytest."""
    from django.conf import settings as django_settings

    # Override some settings for testing
    if not hasattr(django_settings, "DATABASES") or not django_settings.DATABASES.get(
        "default"
    ):
        django_settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        }

    django.setup()


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database."""
    from django.test.utils import setup_test_environment, teardown_test_environment

    setup_test_environment()
    yield
    teardown_test_environment()


@pytest.fixture
def client():
    """Django test client."""
    from django.test import Client

    return Client()


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    from django.contrib.auth import get_user_model
    from tenants.models import Tenant

    User = get_user_model()

    # Create tenant
    tenant = Tenant.objects.create(
        name="Test Church",
        subdomain="testchurch",
        is_active=True,
    )

    # Create admin user
    user = User.objects.create_user(
        email="admin@testchurch.com",
        password="testpassword123",
        first_name="Admin",
        last_name="User",
        tenant=tenant,
        is_staff=True,
    )

    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user for testing."""
    from django.contrib.auth import get_user_model
    from tenants.models import Tenant

    User = get_user_model()

    # Create tenant
    tenant = Tenant.objects.create(
        name="Regular Church",
        subdomain="regchurch",
        is_active=True,
    )

    # Create regular user
    user = User.objects.create_user(
        email="user@regchurch.com",
        password="testpassword123",
        first_name="Regular",
        last_name="User",
        tenant=tenant,
    )

    return user


@pytest.fixture
def tenant(db):
    """Create a tenant for testing."""
    from tenants.models import Tenant

    return Tenant.objects.create(
        name="Test Church",
        subdomain="testchurch",
        is_active=True,
        currency="USD",
    )


@pytest.fixture
def member(db, tenant, admin_user):
    """Create a member for testing."""
    from members.models import Member

    return Member.objects.create(
        tenant=tenant,
        first_name="John",
        last_name="Doe",
        email="john.doe@test.com",
        phone="+1234567890",
        status="active",
    )


@pytest.fixture
def authenticated_client(client, admin_user):
    """Authenticated Django test client."""
    client.force_login(admin_user)
    return client


@pytest.fixture
def api_client():
    """DRF API test client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, admin_user):
    """Authenticated DRF API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


# ============================================================
# E2E Tests Fixtures (Playwright)
# ============================================================


@pytest.fixture(scope="session")
def browser():
    """
    Session-scoped browser instance for E2E tests.
    Requires Playwright to be installed: pip install playwright
    """
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()
        playwright.stop()
    except ImportError:
        pytest.skip("Playwright not installed. Install with: pip install playwright")


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="es-CR",  # Spanish Costa Rica
    )
    page = context.new_page()
    yield page
    page.close()
    context.close()


@pytest.fixture
def live_server_url(live_server):
    """Get the live server URL."""
    return live_server.url


# ============================================================
# Factory Fixtures
# ============================================================


@pytest.fixture
def member_factory(db, tenant):
    """Factory for creating members."""
    from members.models import Member

    def _create_member(
        first_name="Test", last_name="Member", email=None, status="active", **kwargs
    ):
        if email is None:
            email = f"{first_name.lower()}.{last_name.lower()}@test.com"

        return Member.objects.create(
            tenant=tenant,
            first_name=first_name,
            last_name=last_name,
            email=email,
            status=status,
            **kwargs,
        )

    return _create_member


@pytest.fixture
def user_factory(db, tenant):
    """Factory for creating users."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    def _create_user(
        email="testuser@test.com",
        first_name="Test",
        last_name="User",
        is_staff=False,
        **kwargs,
    ):
        return User.objects.create_user(
            email=email,
            password="testpassword123",
            first_name=first_name,
            last_name=last_name,
            tenant=tenant,
            is_staff=is_staff,
            **kwargs,
        )

    return _create_user
