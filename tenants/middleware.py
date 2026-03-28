"""
Multi-tenancy middleware for SG Church.
Handles tenant resolution based on subdomain or path.
"""

from django.http import JsonResponse
from django.db import connection
from tenants.models import Tenant


class TenantMiddleware:
    """
    Middleware to resolve tenant from request and set database schema.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get tenant resolution strategy from settings
        strategy = getattr(request, "tenant_resolution_strategy", "subdomain")

        # Skip for admin, static files, and certain URLs
        if self._should_skip(request):
            return self.get_response(request)

        # Try to resolve tenant
        tenant = self._resolve_tenant(request)

        if tenant:
            # Set tenant on request
            request.tenant = tenant

            # Switch to tenant's schema
            connection.set_schema(tenant.schema_name)
        else:
            request.tenant = None

        response = self.get_response(request)

        # Reset schema after request
        connection.set_schema("public")

        return response

    def _should_skip(self, request):
        """Check if request should skip tenant resolution."""
        # Skip admin
        if request.path.startswith("/admin/"):
            return True

        # Skip static files
        if request.path.startswith("/static/"):
            return True

        # Skip media files
        if request.path.startswith("/media/"):
            return True

        # Skip API health checks
        if request.path in ["/health/", "/api/health/"]:
            return True

        # Skip tenant creation/setup URLs
        if request.path in ["/setup/", "/onboarding/"]:
            return True

        return False

    def _resolve_tenant(self, request):
        """
        Resolve tenant from request based on strategy.
        Supports subdomain and path strategies.
        """
        strategy = getattr(settings, "TENANT_RESOLUTION_STRATEGY", "subdomain")

        if strategy == "subdomain":
            return self._resolve_by_subdomain(request)
        elif strategy == "path":
            return self._resolve_by_path(request)

        return None

    def _resolve_by_subdomain(self, request):
        """Resolve tenant by subdomain."""
        host = request.get_host().split(":")[0]

        # Get base domain from settings
        base_domain = getattr(settings, "BASE_DOMAIN", "localhost")

        # Extract subdomain
        if base_domain in host:
            subdomain = host.replace(f".{base_domain}", "")
            if subdomain != host:  # Successfully extracted subdomain
                try:
                    return Tenant.objects.get(subdomain=subdomain)
                except Tenant.DoesNotExist:
                    pass

        return None

    def _resolve_by_path(self, request):
        """Resolve tenant by URL path."""
        # E.g., /tenant-slug/members/
        path_parts = request.path.strip("/").split("/")

        if path_parts:
            subdomain = path_parts[0]
            try:
                return Tenant.objects.get(subdomain=subdomain)
            except Tenant.DoesNotExist:
                pass

        return None


# Import settings at module level
from django.conf import settings
