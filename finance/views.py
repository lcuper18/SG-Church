"""
Finance views for SG Church.
"""

from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    View,
)
from core.exports import csv_response, export_filename
from core.mixins import ManageFinanceRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.utils.formats import date_format
from django.conf import settings
from datetime import date, datetime, time, timedelta
import stripe

from .models import Donation, Expense, Campaign
from members.models import Member


# ============================================================
# DASHBOARD
# ============================================================


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


# ============================================================
# DONATIONS
# ============================================================


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


# ============================================================
# EXPENSES
# ============================================================


class ExpenseListView(ManageFinanceRequiredMixin, ListView):
    """List all expenses with filters."""

    model = Expense
    template_name = "finance/expenses/list.html"
    context_object_name = "expenses"
    paginate_by = 25

    def get_queryset(self):
        return filtered_expenses(self.request)


expense_list = ExpenseListView.as_view()


class ExpenseCreateView(ManageFinanceRequiredMixin, CreateView):
    """Create a new expense."""

    model = Expense
    template_name = "finance/expenses/form.html"
    fields = [
        "description",
        "amount",
        "category",
        "vendor_name",
        "vendor_email",
        "expense_date",
        "due_date",
        "receipt",
        "notes",
    ]

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
            form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("expense_list")


expense_create = ExpenseCreateView.as_view()


class ExpenseUpdateView(ManageFinanceRequiredMixin, UpdateView):
    """Update an existing expense."""

    model = Expense
    template_name = "finance/expenses/form.html"
    fields = [
        "description",
        "amount",
        "category",
        "status",
        "vendor_name",
        "vendor_email",
        "expense_date",
        "due_date",
        "receipt",
        "approved_by",
        "notes",
    ]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Expense.objects.none()
        return Expense.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("expense_list")


expense_update = ExpenseUpdateView.as_view()


class ExpenseDeleteView(ManageFinanceRequiredMixin, DeleteView):
    """Delete an expense."""

    model = Expense
    template_name = "finance/expenses/confirm_delete.html"
    context_object_name = "expense"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Expense.objects.none()
        return Expense.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("expense_list")


expense_delete = ExpenseDeleteView.as_view()


# ============================================================
# PUBLIC DONATE PAGE
# ============================================================


def donate_page(request):
    """Public donation page."""

    # Get tenant from subdomain or query param
    tenant = None
    subdomain = request.GET.get("church")

    if subdomain:
        from tenants.models import Tenant

        tenant = Tenant.objects.filter(subdomain=subdomain, is_active=True).first()

    if not tenant and request.user.is_authenticated:
        tenant = getattr(request.user, "tenant", None)

    if not tenant:
        return render(
            request, "finance/donate.html", {"error": "Iglesia no encontrada"}
        )

    context = {
        "tenant": tenant,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, "finance/donate.html", context)


def create_checkout_session(request):
    """Create Stripe checkout session for donation."""

    if request.method != "POST":
        return redirect("donate_page")

    from tenants.models import Tenant
    import json

    # Get tenant
    tenant = None
    subdomain = request.POST.get("church")
    if subdomain:
        tenant = Tenant.objects.filter(subdomain=subdomain, is_active=True).first()

    if not tenant and request.user.is_authenticated:
        tenant = getattr(request.user, "tenant", None)

    if not tenant:
        messages.error(request, "Iglesia no encontrada")
        return redirect("donate_page")

    # Get form data
    try:
        amount = float(request.POST.get("amount", 0))
    except ValueError:
        messages.error(request, "Monto inválido")
        return redirect("donate_page")
    campaign = request.POST.get("campaign", "offering")
    donor_name = request.POST.get("donor_name", "")
    donor_email = request.POST.get("donor_email", "")
    cover_fees = request.POST.get("cover_fees") == "on"

    # Sanity bounds before this ever reaches Stripe: guards against typos and
    # abusive input, not a business rule.
    MIN_DONATION_AMOUNT = 1
    MAX_DONATION_AMOUNT = 100_000
    if not (MIN_DONATION_AMOUNT <= amount <= MAX_DONATION_AMOUNT):
        messages.error(
            request,
            f"El monto debe estar entre {MIN_DONATION_AMOUNT} y {MAX_DONATION_AMOUNT}",
        )
        return redirect("donate_page")

    # Calculate fees (Stripe: 2.9% + $0.30)
    if cover_fees:
        fees = (amount * 0.029) + 0.30
        amount += fees

    # Convert to cents
    amount_cents = int(amount * 100)

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": tenant.currency.lower(),
                        "product_data": {
                            "name": f"Donación - {tenant.name}",
                            "description": campaign.capitalize(),
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=request.build_absolute_uri("/donate/success/")
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri("/donate/"),
            metadata={
                "tenant_id": str(tenant.id),
                "campaign": campaign,
                "donor_name": donor_name,
                "donor_email": donor_email,
            },
        )

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        messages.error(request, f"Error al procesar pago: {str(e)}")
        return redirect("donate_page")


def donation_success(request):
    """Success page after donation."""

    session_id = request.GET.get("session_id")

    context = {
        "session_id": session_id,
    }

    return render(request, "finance/donate_success.html", context)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks.

    Exempt from CSRF because Stripe never sends a CSRF token; the request is
    instead authenticated by verifying the Stripe-Signature header below.
    """

    if request.method != "POST":
        return HttpResponse(status=405)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_session(session)
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        handle_payment_failed(invoice)

    return HttpResponse(status=200)


def handle_checkout_session(session):
    """Process completed checkout session."""

    metadata = session.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    campaign = metadata.get("campaign", "offering")
    donor_name = metadata.get("donor_name", "")
    donor_email = metadata.get("donor_email", "")

    if not tenant_id:
        return

    # Find or create member based on email
    member = None
    if donor_email:
        from members.models import Member

        member = Member.objects.filter(
            tenant_id=tenant_id, email__iexact=donor_email
        ).first()

    # Get amount
    amount = session.get("amount_total", 0) / 100

    # Create donation record
    donation = Donation.objects.create(
        tenant_id=tenant_id,
        member=member,
        amount=amount,
        currency=session.get("currency", "usd").upper(),
        campaign=campaign,
        status="completed",
        stripe_payment_intent_id=session.get("payment_intent", ""),
        donor_name=donor_name or (member.full_name if member else "Anonymous"),
        donor_email=donor_email or "",
    )

    # In-app notification for church admins. Kept apart from the receipt below
    # so a failure in one never silently skips the other.
    try:
        from tenants.models import Tenant
        from notifications.models import create_notification
        from django.contrib.auth import get_user_model

        tenant = Tenant.objects.get(id=tenant_id)

        # Get church admins
        admins = get_user_model().objects.filter(tenant=tenant, is_staff=True)

        campaign_display = dict(Donation.CAMPAIGN_CHOICES).get(
            campaign, campaign.title()
        )

        for admin in admins:
            create_notification(
                tenant=tenant,
                user=admin,
                title="Nueva donación recibida",
                message=f"Se recibió una donación de ${amount:.2f} ({campaign_display})",
                notification_type="donation_received",
                link=f"/finance/donations/{donation.pk}/",
                content_type="finance.donation",
                object_id=donation.pk,
            )
    except Exception as e:
        # Log error but don't break the donation flow
        import logging

        logging.exception(f"Error creating donation notification: {e}")

    # Receipt e-mail to the donor, asynchronously.
    try:
        from emails.tasks import send_donation_receipt_task

        send_donation_receipt_task.delay(donation.pk)
    except Exception as e:
        import logging

        logging.exception(f"Error queueing donation receipt: {e}")


def handle_payment_failed(invoice):
    """Handle failed payment."""

    # Find and update donation
    # This would need to match based on Stripe customer info
    pass


# ============================================================
# REPORTS
# ============================================================


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


from django.db.models import Max
from django.http import HttpResponse


# ============================================================
# CSV EXPORTS
# ============================================================


class DonationExportView(ManageFinanceRequiredMixin, View):
    """Download the donations matching the list's current filters."""

    def get(self, request):
        rows = (
            [
                d.donation_date,
                d.member.full_name if d.member else ("Anónimo" if d.anonymous else d.donor_name),
                d.member.email if d.member else d.donor_email,
                d.amount,
                d.currency,
                d.get_campaign_display(),
                d.get_donation_type_display(),
                d.get_status_display(),
                d.payment_method,
                d.notes,
            ]
            for d in filtered_donations(request)
        )
        header = [
            "Fecha", "Donante", "Email", "Monto", "Moneda", "Campaña", "Tipo",
            "Estado", "Método de pago", "Notas",
        ]
        return csv_response(export_filename("donaciones"), header, rows)


donation_export = DonationExportView.as_view()


class ExpenseExportView(ManageFinanceRequiredMixin, View):
    """Download the expenses matching the list's current filters."""

    def get(self, request):
        rows = (
            [
                e.expense_date,
                e.description,
                e.get_category_display(),
                e.vendor_name,
                e.amount,
                e.get_status_display(),
                e.due_date,
            ]
            for e in filtered_expenses(request)
        )
        header = ["Fecha", "Descripción", "Categoría", "Proveedor", "Monto", "Estado", "Vence"]
        return csv_response(export_filename("gastos"), header, rows)


expense_export = ExpenseExportView.as_view()
