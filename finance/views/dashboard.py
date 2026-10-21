"""Finance dashboard."""

from datetime import datetime, time

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.formats import date_format
from django.views.generic import TemplateView

from core.mixins import ManageFinanceRequiredMixin

from ..models import Donation, Expense


class FinanceDashboardView(ManageFinanceRequiredMixin, TemplateView):
    """Finance dashboard with stats and charts."""

    template_name = "finance/dashboard.html"

    @staticmethod
    def _month_bounds(now, months_back):
        """Return (start, end) of the calendar month `months_back` months
        before `now`: start inclusive, end exclusive (first moment of the next
        month). Stepping back by whole calendar months, not by 30 days, so no
        month is skipped or repeated."""
        index = now.year * 12 + (now.month - 1) - months_back
        year, month = divmod(index, 12)
        start = now.replace(
            year=year, month=month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        next_index = index + 1
        next_year, next_month = divmod(next_index, 12)
        end = start.replace(year=next_year, month=next_month + 1)
        return start, end

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if not tenant:
            return context

        now = timezone.localtime()
        month_start, _ = self._month_bounds(now, 0)

        # Last 12 calendar months, oldest first: one grouped query per table
        # instead of two per month.
        windows = [self._month_bounds(now, back) for back in range(11, -1, -1)]
        first_start, last_end = windows[0][0], windows[-1][1]
        donated = {
            (row["month"].year, row["month"].month): row["total"]
            for row in Donation.objects.filter(
                tenant=tenant,
                status="completed",
                donation_date__gte=first_start,
                donation_date__lt=last_end,
            )
            .annotate(month=TruncMonth("donation_date", tzinfo=now.tzinfo))
            .values("month")
            .annotate(total=Sum("amount"))
        }
        spent = {
            (row["month"].year, row["month"].month): row["total"]
            for row in Expense.objects.filter(
                tenant=tenant,
                expense_date__gte=first_start.date(),
                expense_date__lt=last_end.date(),
            )
            .annotate(month=TruncMonth("expense_date"))
            .values("month")
            .annotate(total=Sum("amount"))
        }

        chart_data = []
        for start, _end in windows:
            key = (start.year, start.month)
            chart_data.append(
                {
                    "month": date_format(start, "M"),
                    "donations": float(donated.get(key) or 0),
                    "expenses": float(spent.get(key) or 0),
                }
            )

        # The current month is the last window.
        donations_this_month = donated.get((month_start.year, month_start.month)) or 0
        expenses_this_month = spent.get((month_start.year, month_start.month)) or 0
        balance_this_month = donations_this_month - expenses_this_month

        # Active donors this month
        active_donors = (
            Donation.objects.filter(
                tenant=tenant, status="completed", donation_date__gte=month_start
            )
            .values("member")
            .distinct()
            .count()
        )

        # Recent transactions
        recent_donations = Donation.objects.filter(tenant=tenant).order_by(
            "-donation_date"
        )[:5]

        recent_expenses = Expense.objects.filter(tenant=tenant).order_by(
            "-expense_date"
        )[:5]

        # Combine and sort
        recent_transactions = []
        for d in recent_donations:
            recent_transactions.append(
                {
                    "type": "donation",
                    "description": f"Donation - {d.get_campaign_display()}",
                    "amount": d.amount,
                    "date": d.donation_date,
                    "status": d.status,
                }
            )
        for e in recent_expenses:
            recent_transactions.append(
                {
                    "type": "expense",
                    "description": e.description,
                    "amount": -e.amount,
                    "date": timezone.make_aware(
                        datetime.combine(e.expense_date, time.min)
                    ),
                    "status": e.status,
                }
            )
        recent_transactions.sort(key=lambda x: x["date"], reverse=True)
        recent_transactions = recent_transactions[:10]

        context["tenant"] = tenant
        context["donations_this_month"] = donations_this_month
        context["expenses_this_month"] = expenses_this_month
        context["balance_this_month"] = balance_this_month
        context["active_donors"] = active_donors
        context["chart_data"] = chart_data
        context["recent_transactions"] = recent_transactions

        return context


finance_dashboard = FinanceDashboardView.as_view()
