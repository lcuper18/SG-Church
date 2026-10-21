"""CSV exports."""

from django.views.generic import View

from core.exports import csv_response, export_filename
from core.mixins import ManageFinanceRequiredMixin

from .donations import filtered_donations, filtered_expenses


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
