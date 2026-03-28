"""
Admin configuration for finance app.
"""

from django.contrib import admin
from .models import Donation, Expense, Campaign


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ["amount", "member", "campaign", "status", "donation_date"]
    list_filter = ["status", "campaign", "donation_type"]
    search_fields = ["member__first_name", "member__last_name", "donor_email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "amount", "category", "status", "expense_date"]
    list_filter = ["status", "category"]
    search_fields = ["description", "vendor_name"]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "goal", "start_date", "end_date", "status"]
    list_filter = ["status"]
    search_fields = ["name"]
