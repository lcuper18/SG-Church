"""
Core views for SG Church.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

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
