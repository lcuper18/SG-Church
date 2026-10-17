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
    """Only roles that manage members may touch the member directory at all
    (read included — it carries phones, addresses and birth dates)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.can_manage_members)


class CanManageEvents(BasePermission):
    """The event calendar is public inside the church: any authenticated user
    can read it; only roles that manage members can change it."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.can_manage_members


class CanViewRoster(BasePermission):
    """Read-only access to who is enrolled/registered (names, not the full
    directory): member managers and teachers."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and request.method in SAFE_METHODS
            and user.can_view_roster
        )


class CanManageEducation(BasePermission):
    """Any authenticated tenant user can browse the course catalog; only
    certain roles can create/update/delete courses and blocks."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.can_manage_education
