"""Expense list, create, update and delete."""

from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import ManageFinanceRequiredMixin

from ..models import Expense
from .donations import filtered_expenses


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
