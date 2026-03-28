"""
Tenant context utilities.
Provides helpers for accessing tenant information in views and templates.
"""

from django.db import connection
from functools import lru_cache
from typing import Optional
from .models import Tenant


def get_current_tenant() -> Optional[Tenant]:
    """
    Get the current tenant from the request.
    Requires TenantMiddleware to have set request.tenant.
    """
    # This will be set by the middleware
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.utils.deprecation import MiddlewareMixin

    # Try to get from thread-local storage set by middleware
    return getattr(get_current_tenant, "_tenant", None)


def get_tenant_from_request(request) -> Optional[Tenant]:
    """
    Get tenant from request object.
    Set by TenantMiddleware.
    """
    return getattr(request, "tenant", None)


def get_tenant_schema() -> str:
    """
    Get the current tenant's schema name.
    Returns 'public' if no tenant is active.
    """
    schema = getattr(connection, "schema_name", "public")
    if not schema or schema == "public":
        return "public"
    return schema


def get_tenant_from_schema(schema_name: str) -> Optional[Tenant]:
    """
    Get tenant by schema name.
    """
    try:
        return Tenant.objects.get(schema_name=schema_name)
    except Tenant.DoesNotExist:
        return None


def get_tenant_subdomain_from_host(host: str, base_domain: str) -> Optional[str]:
    """
    Extract subdomain from host.

    Example:
        host='miiglesia.sgchurch.app', base_domain='sgchurch.app'
        returns: 'miiglesia'
    """
    if base_domain in host:
        subdomain = host.replace(f".{base_domain}", "")
        if subdomain != host:
            return subdomain
    return None


class TenantContext:
    """
    Context manager for temporarily switching tenant schema.

    Usage:
        with TenantContext(tenant):
            # Code runs with tenant's schema
            members = Member.objects.all()  # Only tenant's members
    """

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.old_schema = None

    def __enter__(self):
        self.old_schema = connection.schema_name
        connection.set_schema(self.tenant.schema_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        connection.set_schema(self.old_schema or "public")
        return False


def require_tenant(view_func):
    """
    Decorator to require a tenant in the request.
    Returns 404 if no tenant is found.
    """
    from functools import wraps
    from django.http import Http404

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        tenant = get_tenant_from_request(request)
        if not tenant:
            raise Http404("Tenant not found")
        return view_func(request, *args, **kwargs)

    return wrapper


def get_tenant_users(tenant: Tenant):
    """
    Get all users for a tenant.
    """
    return tenant.users.all()


def get_tenant_members(tenant: Tenant):
    """
    Get all members for a tenant.
    """
    return tenant.members.all()


def get_tenant_stats(tenant: Tenant):
    """
    Get basic statistics for a tenant.
    """
    return {
        "total_members": tenant.members.count(),
        "total_users": tenant.users.count(),
        "total_donations": tenant.donations.count(),
        "total_families": tenant.families.count(),
        "active_members": tenant.members.filter(member_status="member").count(),
    }
