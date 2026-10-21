"""Finance reports."""

from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Count, Max, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from core.mixins import ManageFinanceRequiredMixin

from ..models import Donation, Expense
from .dashboard import FinanceDashboardView
from .donations import _parse_date


class IncomeStatementView(ManageFinanceRequiredMixin, TemplateView):
    """Income statement report."""

    template_name = "finance/reports/income_statement.html"

    def _int_param(self, name, default, low, high):
        try:
            return min(max(int(self.request.GET.get(name, default)), low), high)
        except (TypeError, ValueError):
            return default

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["month_choices"] = range(1, 13)
        context["year_choices"] = range(2024, timezone.localdate().year + 1)
        tenant = getattr(self.request.user, "tenant", None)

        if not tenant:
            return context

        # Month/year from the query string (clamped, so junk can't crash the
        # page), defaulting to the current month in the church's time zone.
        today = timezone.localdate()
        month = self._int_param("month", today.month, 1, 12)
        year = self._int_param("year", today.year, 2024, today.year)

        # Calendar-month bounds in the church's time zone: start inclusive,
        # end exclusive (first moment of the next month).
        reference = timezone.make_aware(datetime(year, month, 1, 12))
        start_date, end_date = FinanceDashboardView._month_bounds(reference, 0)

        # Donations by campaign
        donations_by_campaign = (
            Donation.objects.filter(
                tenant=tenant,
                status="completed",
                donation_date__gte=start_date,
                donation_date__lt=end_date,
            )
            .values("campaign")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        total_donations = sum(d["total"] or 0 for d in donations_by_campaign)

        # Expenses by category
        expenses_by_category = (
            Expense.objects.filter(
                tenant=tenant,
                expense_date__gte=start_date.date(),
                expense_date__lt=end_date.date(),
            )
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        total_expenses = sum(e["total"] or 0 for e in expenses_by_category)

        context["tenant"] = tenant
        context["month"] = month
        context["year"] = year
        context["donations_by_campaign"] = list(donations_by_campaign)
        context["total_donations"] = total_donations
        context["expenses_by_category"] = list(expenses_by_category)
        context["total_expenses"] = total_expenses
        context["net_balance"] = total_donations - total_expenses

        return context


income_statement = IncomeStatementView.as_view()


class DonationsByMemberView(ManageFinanceRequiredMixin, TemplateView):
    """Donations grouped by member."""

    template_name = "finance/reports/donations_by_member.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if not tenant:
            return context

        # Date range (inclusive of the whole last day, like the donation list)
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        donations = Donation.objects.filter(tenant=tenant, status="completed")
        if _parse_date(date_from):
            donations = donations.filter(donation_date__date__gte=_parse_date(date_from))
        if _parse_date(date_to):
            donations = donations.filter(donation_date__date__lte=_parse_date(date_to))

        # Group by member
        donations_by_member = (
            donations.values(
                "member__id", "member__first_name", "member__last_name", "member__email"
            )
            .annotate(
                total_donated=Sum("amount"),
                donation_count=Count("id"),
                last_donation=Max("donation_date"),
            )
            .order_by("-total_donated")
        )

        # Also include anonymous donors
        anonymous_donations = donations.filter(
            anonymous=True, member__isnull=True
        ).aggregate(total=Sum("amount"), count=Count("id"))

        context["tenant"] = tenant
        page = Paginator(donations_by_member, 50).get_page(self.request.GET.get("page"))
        context["donations_by_member"] = page
        context["page_obj"] = page
        context["anonymous_total"] = anonymous_donations["total"] or 0
        context["anonymous_count"] = anonymous_donations["count"] or 0
        context["date_from"] = date_from
        context["date_to"] = date_to

        return context


donations_by_member = DonationsByMemberView.as_view()
