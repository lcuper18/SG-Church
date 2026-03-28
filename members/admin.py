"""
Admin configuration for members app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Member, Family


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "tenant",
        "is_active",
    ]
    list_filter = ["role", "is_active", "tenant"]
    search_fields = ["username", "email", "first_name", "last_name"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Tenant Info", {"fields": ("tenant", "role", "member_profile")}),
    )


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "member_status", "tenant", "created_at"]
    list_filter = ["member_status", "gender", "marital_status"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "head_of_family", "member_count", "created_at"]
    list_filter = ["tenant"]
    search_fields = ["name", "head_of_family__first_name", "head_of_family__last_name"]
