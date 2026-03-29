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
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import stripe

from .models import Donation, Expense, Campaign
from members.models import Member


# ============================================================
# DASHBOARD
# ============================================================


class FinanceDashboardView(LoginRequiredMixin, TemplateView):
    """Finance dashboard with stats and charts."""

    template_name = "finance/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if not tenant:
            return context

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        year_start = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # Calculate stats for current month
        donations_this_month = (
            Donation.objects.filter(
                tenant=tenant, status="completed", donation_date__gte=month_start
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        expenses_this_month = (
            Expense.objects.filter(
                tenant=tenant, expense_date__gte=month_start
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

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

        # Chart data - last 12 months
        chart_data = []
        for i in range(11, -1, -1):
            # Calculate month range
            if i == 0:
                month_start_data = month_start
                month_end = now
            else:
                # Go back i months
                month_date = now - timedelta(days=30 * i)
                month_start_data = month_date.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if month_date.month == 12:
                    month_end = month_date.replace(
                        month=12, day=31, hour=23, minute=59, second=59
                    )
                else:
                    next_month = month_date.replace(month=month_date.month + 1, day=1)
                    month_end = next_month - timedelta(seconds=1)

            month_donations = (
                Donation.objects.filter(
                    tenant=tenant,
                    status="completed",
                    donation_date__gte=month_start_data,
                    donation_date__lte=month_end,
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            month_expenses = (
                Expense.objects.filter(
                    tenant=tenant,
                    expense_date__gte=month_start_data,
                    expense_date__lte=month_end.date(),
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            chart_data.append(
                {
                    "month": month_start_data.strftime("%b"),
                    "donations": float(month_donations),
                    "expenses": float(month_expenses),
                }
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
                    "date": e.expense_date,
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


class DonationListView(LoginRequiredMixin, ListView):
    """List all donations with filters."""

    model = Donation
    template_name = "finance/donations/list.html"
    context_object_name = "donations"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Donation.objects.none()

        queryset = Donation.objects.filter(tenant=tenant)

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Filter by campaign
        campaign = self.request.GET.get("campaign")
        if campaign:
            queryset = queryset.filter(campaign=campaign)

        # Filter by member
        member_id = self.request.GET.get("member")
        if member_id:
            queryset = queryset.filter(member_id=member_id)

        # Filter by date range
        date_from = self.request.GET.get("date_from")
        if date_from:
            queryset = queryset.filter(donation_date__gte=date_from)

        date_to = self.request.GET.get("date_to")
        if date_to:
            queryset = queryset.filter(donation_date__lte=date_to)

        # Search
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(donor_name__icontains=search)
                | Q(donor_email__icontains=search)
                | Q(member__first_name__icontains=search)
                | Q(member__last_name__icontains=search)
            )

        return queryset.select_related("member").order_by("-donation_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if tenant:
            context["members"] = Member.objects.filter(tenant=tenant)

        return context


donation_list = DonationListView.as_view()


class DonationDetailView(LoginRequiredMixin, DetailView):
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


class ExpenseListView(LoginRequiredMixin, ListView):
    """List all expenses with filters."""

    model = Expense
    template_name = "finance/expenses/list.html"
    context_object_name = "expenses"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Expense.objects.none()

        queryset = Expense.objects.filter(tenant=tenant)

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Filter by category
        category = self.request.GET.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Filter by date range
        date_from = self.request.GET.get("date_from")
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)

        date_to = self.request.GET.get("date_to")
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)

        return queryset.order_by("-expense_date")


expense_list = ExpenseListView.as_view()


class ExpenseCreateView(LoginRequiredMixin, CreateView):
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


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
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


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
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
    amount = float(request.POST.get("amount", 0))
    campaign = request.POST.get("campaign", "offering")
    donor_name = request.POST.get("donor_name", "")
    donor_email = request.POST.get("donor_email", "")
    cover_fees = request.POST.get("cover_fees") == "on"

    if amount <= 0:
        messages.error(request, "Monto inválido")
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


def stripe_webhook(request):
    """Handle Stripe webhooks."""

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
    Donation.objects.create(
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


def handle_payment_failed(invoice):
    """Handle failed payment."""

    # Find and update donation
    # This would need to match based on Stripe customer info
    pass


# ============================================================
# REPORTS
# ============================================================


class IncomeStatementView(LoginRequiredMixin, TemplateView):
    """Income statement report."""

    template_name = "finance/reports/income_statement.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if not tenant:
            return context

        # Get month/year from query params or use current
        month = int(self.request.GET.get("month", timezone.now().month))
        year = int(self.request.GET.get("year", timezone.now().year))

        # Calculate date range
        from calendar import monthrange

        start_date = timezone.datetime(year, month, 1)
        end_date = timezone.datetime(
            year, month, day=monthrange(year, month)[1], hour=23, minute=59, second=59
        )

        # Donations by campaign
        donations_by_campaign = (
            Donation.objects.filter(
                tenant=tenant,
                status="completed",
                donation_date__gte=start_date,
                donation_date__lte=end_date,
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
                expense_date__lte=end_date.date(),
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


class DonationsByMemberView(LoginRequiredMixin, TemplateView):
    """Donations grouped by member."""

    template_name = "finance/reports/donations_by_member.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if not tenant:
            return context

        # Get date range
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        # Base queryset
        donations = Donation.objects.filter(tenant=tenant, status="completed")

        if date_from:
            donations = donations.filter(donation_date__gte=date_from)
        if date_to:
            donations = donations.filter(donation_date__lte=date_to)

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
        context["donations_by_member"] = list(donations_by_member)
        context["anonymous_total"] = anonymous_donations["total"] or 0
        context["anonymous_count"] = anonymous_donations["count"] or 0
        context["date_from"] = date_from
        context["date_to"] = date_to

        return context


donations_by_member = DonationsByMemberView.as_view()


from django.db.models import Max
from django.http import HttpResponse
