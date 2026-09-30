"""
Role-based DRF permission classes.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class CanManageFinance(BasePermission):
    """Only roles that can manage finance may access finance endpoints at all
    (read included — donation/expense data is sensitive)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.can_manage_finance)


class CanManageMembers(BasePermission):
    """Any authenticated tenant user can read the member directory; only
    certain roles can create/update/delete."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.can_manage_members
