"""
Multi-tenancy middleware for SG Church.

Tenant isolation is enforced at the row level (every tenant-owned model has
a `tenant` FK, filtered per-query) rather than via separate database
schemas. This middleware only resolves which Tenant a request belongs to
and exposes it as `request.tenant` — it does not touch the database
connection or switch schemas.
"""

from django.conf import settings
from tenants.models import Tenant


class TenantMiddleware:
    """
    Resolves the current Tenant from the request (by subdomain, or by
    falling back to the single tenant on a standalone/single-church
    install) and sets it as `request.tenant`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_skip(request):
            request.tenant = None
            return self.get_response(request)

        request.tenant = self._resolve_tenant(request)

        return self.get_response(request)

    def _should_skip(self, request):
        """Check if request should skip tenant resolution."""
        skip_prefixes = ("/admin/", "/static/", "/media/", "/onboarding/")
        if request.path.startswith(skip_prefixes):
            return True

        if request.path in ["/health/", "/api/health/"]:
            return True

        return False

    def _resolve_tenant(self, request):
        """
        Resolve tenant from request based on the configured strategy,
        falling back to "the only tenant" when there's exactly one
        (standalone/single-church installs, where no subdomain routing is
        configured).
        """
        strategy = getattr(settings, "TENANT_RESOLUTION_STRATEGY", "subdomain")

        if strategy == "subdomain":
            tenant = self._resolve_by_subdomain(request)
        elif strategy == "path":
            tenant = self._resolve_by_path(request)
        else:
            tenant = None

        if tenant:
            return tenant

        return self._resolve_single_tenant_fallback()

    def _resolve_by_subdomain(self, request):
        """Resolve tenant by subdomain."""
        host = request.get_host().split(":")[0]
        base_domain = getattr(settings, "BASE_DOMAIN", "localhost")

        if base_domain in host:
            subdomain = host.replace(f".{base_domain}", "")
            if subdomain != host:  # Successfully extracted subdomain
                return Tenant.objects.filter(subdomain=subdomain).first()

        return None

    def _resolve_by_path(self, request):
        """Resolve tenant by URL path, e.g. /tenant-slug/members/."""
        path_parts = request.path.strip("/").split("/")

        if path_parts and path_parts[0]:
            return Tenant.objects.filter(subdomain=path_parts[0]).first()

        return None

    def _resolve_single_tenant_fallback(self):
        """
        Standalone/single-church installs have exactly one Tenant and no
        real subdomain routing (e.g. accessed via localhost or a bare
        server IP) — use that one tenant rather than requiring subdomain
        configuration.
        """
        tenants = list(Tenant.objects.filter(is_active=True)[:2])
        if len(tenants) == 1:
            return tenants[0]
        return None
