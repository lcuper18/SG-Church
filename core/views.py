"""
Core views for SG Church.
"""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.utils import timezone
from datetime import timedelta

from core.forms import ChurchSettingsForm, ProfileForm, StyledPasswordChangeForm
from core.mixins import ChurchAdminRequiredMixin
from members.models import Member
from tenants.models import Tenant
from finance.models import Donation


def home(request):
    """Home page."""
    # If user is logged in and has completed onboarding, redirect to dashboard
    if request.user.is_authenticated:
        tenant = getattr(request.user, "tenant", None)
        if tenant and tenant.onboarding_completed:
            return redirect("dashboard")
        elif tenant:
            return redirect("onboarding_start")
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    """Dashboard for logged-in users."""
    user = request.user
    tenant = getattr(user, "tenant", None)

    if not tenant:
        # No tenant yet - show onboarding
        return redirect("onboarding_start")

    if not tenant.onboarding_completed:
        # Onboarding not completed
        return redirect("onboarding_start")

    # Calculate stats
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total members
    total_members = Member.objects.filter(tenant=tenant).count()

    # New members this month
    new_members_this_month = Member.objects.filter(
        tenant=tenant, created_at__gte=month_start
    ).count()

    # Members by status
    members_as_member = Member.objects.filter(
        tenant=tenant, member_status="member"
    ).count()
    members_as_visitor = Member.objects.filter(
        tenant=tenant, member_status="visitor"
    ).count()
    members_as_attendee = Member.objects.filter(
        tenant=tenant, member_status="attendee"
    ).count()
    members_inactive = Member.objects.filter(
        tenant=tenant, member_status="inactive"
    ).count()

    # Donations this month
    donations_this_month = (
        Donation.objects.filter(
            tenant=tenant, status="completed", donation_date__gte=month_start
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # Recent members
    recent_members = Member.objects.filter(tenant=tenant).order_by("-created_at")[:5]

    context = {
        "tenant": tenant,
        "total_members": total_members,
        "new_members_this_month": new_members_this_month,
        "members_as_member": members_as_member,
        "members_as_visitor": members_as_visitor,
        "members_as_attendee": members_as_attendee,
        "members_inactive": members_inactive,
        "donations_this_month": donations_this_month,
        "recent_members": recent_members,
    }

    return render(request, "core/dashboard.html", context)


@login_required
def profile(request):
    """Edit the user's name and change their password."""
    user = request.user
    profile_form = ProfileForm(instance=user)
    password_form = StyledPasswordChangeForm(user)

    if request.method == "POST":
        if request.POST.get("action") == "password":
            password_form = StyledPasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)  # keep the user logged in
                messages.success(request, "Contraseña actualizada.")
                return redirect("profile")
        else:
            profile_form = ProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Perfil actualizado.")
                return redirect("profile")

    return render(
        request,
        "core/profile.html",
        {"profile_form": profile_form, "password_form": password_form},
    )


class ChurchSettingsView(LoginRequiredMixin, ChurchAdminRequiredMixin, UpdateView):
    """Church-wide settings; administrators only."""

    form_class = ChurchSettingsForm
    template_name = "core/church_settings.html"
    success_url = reverse_lazy("church_settings")

    def get_object(self, queryset=None):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            raise Http404("Este usuario no pertenece a ninguna iglesia.")
        return tenant

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.object
        context["has_financial_data"] = (
            tenant.donations.exists() or tenant.expenses.exists()
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "Configuración guardada.")
        return super().form_valid(form)
