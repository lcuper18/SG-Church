"""
Pytest configuration and fixtures for SG Church tests.
"""

import concurrent.futures
import os
import pytest

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sg_church.settings.test")

# Dedicated OS thread that owns Playwright's entire lifecycle for the whole
# test session (start, browser launch, every page interaction, and -- via
# pytest_pyfunc_call below -- the E2E test bodies themselves). Playwright's
# sync API can only be driven from the thread that started it (it relies on
# greenlets, which are thread-local), and that thread ends up with a
# "running" asyncio event loop for the rest of the process (confirmed via
# asyncio.get_running_loop() right after sync_playwright().start() +
# browser.launch()). That trips Django's @async_unsafe guard on any later
# same-thread DB operation. Keeping Playwright fully confined to this one
# worker thread, and never touching it from pytest's main thread, keeps the
# main thread -- where pytest-django does all its DB setup -- free of that
# poisoning entirely, regardless of fixture/test ordering.
_playwright_thread_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="playwright-worker"
)


def pytest_pyfunc_call(pyfuncitem):
    """Run E2E test bodies on the Playwright worker thread instead of
    pytest's main thread -- see `_playwright_thread_pool` above. Since
    `browser`/`page` are created on that worker thread, every call into
    them, including the ones the test function itself makes, has to happen
    on that same thread too."""
    if "page" in pyfuncitem.fixturenames or "browser" in pyfuncitem.fixturenames:
        testfunction = pyfuncitem.obj
        funcargs = pyfuncitem.funcargs
        testargs = {arg: funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        _playwright_thread_pool.submit(testfunction, **testargs).result()
        return True
    return None


@pytest.fixture
def client():
    """Django test client."""
    from django.test import Client

    return Client()


@pytest.fixture
def client():
    """Django test client."""
    from django.test import Client

    return Client()


import uuid


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    from django.contrib.auth import get_user_model
    from tenants.models import Tenant

    User = get_user_model()

    # Create unique tenant for this test
    unique_id = uuid.uuid4().hex[:8]
    tenant = Tenant.objects.create(
        name="Test Church",
        subdomain=f"testchurch-{unique_id}",
        is_active=True,
    )

    # Create admin user
    user = User.objects.create_user(
        email=f"admin@testchurch-{unique_id}.com",
        password="testpassword123",
        first_name="Admin",
        last_name="User",
        tenant=tenant,
        is_staff=True,
        role="admin",
    )

    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user for testing."""
    from django.contrib.auth import get_user_model
    from tenants.models import Tenant

    User = get_user_model()

    # Create unique tenant
    unique_id = uuid.uuid4().hex[:8]
    tenant = Tenant.objects.create(
        name="Regular Church",
        subdomain=f"regchurch-{unique_id}",
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

    unique_id = uuid.uuid4().hex[:8]
    return Tenant.objects.create(
        name="Test Church",
        subdomain=f"testchurch-{unique_id}",
        is_active=True,
        currency="USD",
    )


@pytest.fixture
def member(db, admin_user):
    """Create a member for testing (same tenant as admin_user)."""
    from members.models import Member

    return Member.objects.create(
        tenant=admin_user.tenant,  # Use admin's tenant
        first_name="John",
        last_name="Doe",
        email="john.doe@test.com",
        phone="+1234567890",
        member_status="active",
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


@pytest.fixture
def regular_api_client(api_client, regular_user):
    """DRF API client authenticated as a low-privilege ('member' role) user."""
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def regular_client(client, regular_user):
    """Django test client authenticated as a low-privilege ('member' role) user."""
    client.force_login(regular_user)
    return client


@pytest.fixture
def regular_user_same_tenant(db, admin_user):
    """A low-privilege ('member' role) user in admin_user's own tenant — lets
    RBAC tests tell "denied by role" apart from "denied by tenant scoping"."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    unique_id = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        email=f"member-{unique_id}@testchurch.com",
        password="testpassword123",
        first_name="Regular",
        last_name="Member",
        tenant=admin_user.tenant,
    )


@pytest.fixture
def regular_api_client_same_tenant(api_client, regular_user_same_tenant):
    """DRF API client for a 'member' role user in admin_user's own tenant."""
    api_client.force_authenticate(user=regular_user_same_tenant)
    return api_client


@pytest.fixture
def regular_client_same_tenant(client, regular_user_same_tenant):
    """Django test client for a 'member' role user in admin_user's own tenant."""
    client.force_login(regular_user_same_tenant)
    return client


# ============================================================
# E2E Tests Fixtures (Playwright)
# ============================================================


@pytest.fixture(scope="session")
def browser():
    """
    Session-scoped browser instance for E2E tests.
    Requires Playwright to be installed: pip install playwright

    Started, and later stopped, on `_playwright_thread_pool`'s dedicated
    worker thread (see the top of this file) rather than directly here, so
    that thread -- not pytest's main thread -- is the one that ends up with
    Playwright's "running" asyncio event loop.
    """

    def _start():
        from playwright.sync_api import sync_playwright

        playwright_ctx = sync_playwright().start()
        browser_instance = playwright_ctx.chromium.launch(headless=True)
        return playwright_ctx, browser_instance

    try:
        playwright_ctx, browser_instance = _playwright_thread_pool.submit(_start).result()
    except ImportError:
        pytest.skip("Playwright not installed. Install with: pip install playwright")
        return

    yield browser_instance

    def _stop():
        browser_instance.close()
        playwright_ctx.stop()

    _playwright_thread_pool.submit(_stop).result()


@pytest.fixture
def page(browser):
    """Create a new page for each test, on the same Playwright worker
    thread that created `browser`."""

    def _open():
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="es-CR",  # Spanish Costa Rica
        )
        return context, context.new_page()

    context, page_instance = _playwright_thread_pool.submit(_open).result()
    yield page_instance

    def _close():
        page_instance.close()
        context.close()

    _playwright_thread_pool.submit(_close).result()


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


@pytest.fixture
def course_factory(db, tenant):
    """Factory for creating courses."""
    from education.models import Course

    def _create_course(title="Test Course", **kwargs):
        return Course.objects.create(tenant=tenant, title=title, **kwargs)

    return _create_course


@pytest.fixture
def course_block_factory(db, tenant):
    """Factory for creating course blocks."""
    from education.models import CourseBlock

    def _create_block(name="Test Block", **kwargs):
        return CourseBlock.objects.create(tenant=tenant, name=name, **kwargs)

    return _create_block
