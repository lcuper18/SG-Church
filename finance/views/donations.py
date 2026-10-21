"""Donation list, create, update and delete."""

from datetime import date

from django.db.models import Q
from django.views.generic import DetailView, ListView

from core.mixins import ManageFinanceRequiredMixin
from members.models import Member

from ..models import Donation, Expense


def filtered_donations(request):
    """The tenant's donations narrowed by the list page's query-string filters
    (shared by the list and its CSV export)."""
    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        return Donation.objects.none()

    queryset = Donation.objects.filter(tenant=tenant)

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    campaign = request.GET.get("campaign")
    if campaign:
        queryset = queryset.filter(campaign=campaign)

    member_id = request.GET.get("member")
    if member_id:
        queryset = queryset.filter(member_id=member_id)

    # Whole days in the church's time zone: "hasta 31/10" includes the 31st
    # (comparing the datetime to a bare date cut it off at midnight).
    date_from = _parse_date(request.GET.get("date_from"))
    if date_from:
        queryset = queryset.filter(donation_date__date__gte=date_from)

    date_to = _parse_date(request.GET.get("date_to"))
    if date_to:
        queryset = queryset.filter(donation_date__date__lte=date_to)

    search = request.GET.get("search")
    if search:
        queryset = queryset.filter(
            Q(donor_name__icontains=search)
            | Q(donor_email__icontains=search)
            | Q(member__first_name__icontains=search)
            | Q(member__last_name__icontains=search)
        )

    return queryset.select_related("member").order_by("-donation_date")


def filtered_expenses(request):
    """The tenant's expenses narrowed by the list page's filters."""
    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        return Expense.objects.none()

    queryset = Expense.objects.filter(tenant=tenant)

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    category = request.GET.get("category")
    if category:
        queryset = queryset.filter(category=category)

    date_from = _parse_date(request.GET.get("date_from"))
    if date_from:
        queryset = queryset.filter(expense_date__gte=date_from)

    date_to = _parse_date(request.GET.get("date_to"))
    if date_to:
        queryset = queryset.filter(expense_date__lte=date_to)

    return queryset.order_by("-expense_date")


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class DonationListView(ManageFinanceRequiredMixin, ListView):
    """List all donations with filters."""

    model = Donation
    template_name = "finance/donations/list.html"
    context_object_name = "donations"
    paginate_by = 25

    def get_queryset(self):
        return filtered_donations(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if tenant:
            context["members"] = Member.objects.filter(tenant=tenant)

        return context


donation_list = DonationListView.as_view()


class DonationDetailView(ManageFinanceRequiredMixin, DetailView):
    """Donation detail view."""

    model = Donation
    template_name = "finance/donations/detail.html"
    context_object_name = "donation"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Donation.objects.none()
        return Donation.objects.filter(tenant=tenant)


donation_detail = DonationDetailView.as_view()
