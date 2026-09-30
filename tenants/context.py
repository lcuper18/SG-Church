"""
Tenant context utilities.
Provides helpers for accessing tenant information in views and templates.

Tenant isolation here is row-level (every tenant-owned model filters by its
`tenant` FK) — there is no per-tenant database schema, so these helpers only
work with `request.tenant` / `Tenant` objects directly, not connection state.
"""

from functools import wraps
from typing import Optional

from django.http import Http404

from .models import Tenant


def get_tenant_from_request(request) -> Optional[Tenant]:
    """
    Get tenant from request object.
    Set by TenantMiddleware.
    """
    return getattr(request, "tenant", None)


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


def require_tenant(view_func):
    """
    Decorator to require a tenant in the request.
    Returns 404 if no tenant is found.
    """

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
