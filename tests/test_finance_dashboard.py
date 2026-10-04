"""
Finance dashboard with real data. The page crashed with a TypeError whenever a
church had both a donation and an expense (it sorted datetimes against dates),
and the 12-month chart stepped back 30 days at a time so months could repeat.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from finance.models import Donation, Expense
from finance.views import FinanceDashboardView


def _month_start_back(months_back):
    now = timezone.localtime()
    index = now.year * 12 + (now.month - 1) - months_back
    year, month = divmod(index, 12)
    return now.replace(year=year, month=month + 1, day=1, hour=12, minute=0, second=0)


def _donation(tenant, amount, when, status="completed"):
    donation = Donation.objects.create(
        tenant=tenant, amount=Decimal(amount), status=status
    )
    Donation.objects.filter(pk=donation.pk).update(donation_date=when)  # auto_now_add
    return donation


@pytest.mark.django_db
class TestMonthBounds:
    def test_steps_whole_calendar_months(self):
        now = timezone.localtime().replace(year=2026, month=3, day=31)
        starts = [FinanceDashboardView._month_bounds(now, n)[0] for n in range(0, 4)]
        assert [(s.year, s.month) for s in starts] == [
            (2026, 3), (2026, 2), (2026, 1), (2025, 12),
        ]

    def test_end_is_start_of_next_month_across_year_end(self):
        now = timezone.localtime().replace(year=2026, month=1, day=15)
        start, end = FinanceDashboardView._month_bounds(now, 1)
        assert (start.year, start.month, start.day) == (2025, 12, 1)
        assert (end.year, end.month, end.day) == (2026, 1, 1)

    def test_thirty_day_stepping_would_have_skipped_a_month(self):
        # The old code did now - 30*i days: from Mar 31 that lands on Mar 1
        # for i=1 (same month again) and skips February entirely.
        now = timezone.localtime().replace(year=2026, month=3, day=31)
        months = {FinanceDashboardView._month_bounds(now, n)[0].month for n in range(0, 3)}
        assert months == {3, 2, 1}


@pytest.mark.django_db
class TestDashboardWithData:
    def test_renders_with_donations_and_expenses(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        _donation(tenant, "50.00", timezone.now())
        Expense.objects.create(
            tenant=tenant, description="Luz", amount=Decimal("20.00"),
            category="utilities", expense_date=date.today(),
        )

        response = authenticated_client.get("/finance/")

        assert response.status_code == 200

    def test_recent_transactions_mix_donations_and_expenses_newest_first(
        self, authenticated_client, admin_user
    ):
        tenant = admin_user.tenant
        _donation(tenant, "10.00", timezone.now() - timedelta(days=3))
        Expense.objects.create(
            tenant=tenant, description="Agua", amount=Decimal("5.00"),
            category="utilities", expense_date=date.today() - timedelta(days=1),
        )
        _donation(tenant, "30.00", timezone.now() - timedelta(days=6))

        recent = authenticated_client.get("/finance/").context["recent_transactions"]

        assert [t["type"] for t in recent] == ["expense", "donation", "donation"]

    def test_chart_has_twelve_distinct_months_with_amounts_in_the_right_one(
        self, authenticated_client, admin_user
    ):
        tenant = admin_user.tenant
        _donation(tenant, "100.00", _month_start_back(2))
        _donation(tenant, "40.00", _month_start_back(2) + timedelta(days=10))
        _donation(tenant, "7.00", _month_start_back(5))
        _donation(tenant, "999.00", _month_start_back(1), status="failed")
        Expense.objects.create(
            tenant=tenant, description="Salario", amount=Decimal("60.00"),
            category="salaries", expense_date=_month_start_back(2).date(),
        )

        chart = authenticated_client.get("/finance/").context["chart_data"]

        assert len(chart) == 12
        assert len({row["month"] for row in chart}) == 12
        # chart is oldest first, so months_back = 11 - index
        assert chart[11 - 2]["donations"] == 140.0
        assert chart[11 - 2]["expenses"] == 60.0
        assert chart[11 - 5]["donations"] == 7.0
        assert chart[11 - 1]["donations"] == 0  # failed donation not counted
        assert sum(row["donations"] for row in chart) == 147.0

    def test_this_month_totals(self, authenticated_client, admin_user):
        tenant = admin_user.tenant
        _donation(tenant, "80.00", timezone.now())
        _donation(tenant, "20.00", timezone.now())
        Expense.objects.create(
            tenant=tenant, description="Gasto", amount=Decimal("30.00"),
            category="other", expense_date=date.today(),
        )

        ctx = authenticated_client.get("/finance/").context

        assert ctx["donations_this_month"] == Decimal("100.00")
        assert ctx["expenses_this_month"] == Decimal("30.00")
        assert ctx["balance_this_month"] == Decimal("70.00")
