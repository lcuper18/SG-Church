"""
Role-based access mixins for class-based (web) views.

Built on Django's UserPassesTestMixin, whose default handle_no_permission()
already does the right thing: an anonymous user is redirected to login, an
authenticated user who fails the test gets a 403 (PermissionDenied).
"""

from django.contrib.auth.mixins import UserPassesTestMixin


class ManageFinanceRequiredMixin(UserPassesTestMixin):
    """Require the logged-in user's role to allow managing finance."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_manage_finance


class ManageMembersRequiredMixin(UserPassesTestMixin):
    """Require the logged-in user's role to allow managing members."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_manage_members


class ManageEducationRequiredMixin(UserPassesTestMixin):
    """Require the logged-in user's role to allow managing education (courses)."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_manage_education


class ChurchAdminRequiredMixin(UserPassesTestMixin):
    """Require the logged-in user to be an administrator of their church."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_church_admin
