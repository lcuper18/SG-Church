"""
Admin configuration for tenants app.
"""

from django.contrib import admin
from .models import Tenant, TenantDomain


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "subdomain", "email", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "subdomain", "email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(TenantDomain)
class TenantDomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "tenant", "is_primary", "is_verified"]
    list_filter = ["is_primary", "is_verified"]
    search_fields = ["domain", "tenant__name"]
