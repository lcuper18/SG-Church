"""
Finance models for SG Church.
Handles donations and accounting.
"""

from django.db import models
import uuid


class Donation(models.Model):
    """
    Represents a donation from a member.
    """

    TYPE_CHOICES = [
        ("one_time", "One Time"),
        ("recurring", "Recurring"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    CAMPAIGN_CHOICES = [
        ("tithe", "Tithe"),
        ("offering", "General Offering"),
        ("building", "Building Fund"),
        ("missions", "Missions"),
        ("youth", "Youth"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant (church)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="donations"
    )

    # Member who made the donation
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
    )

    # Donation details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    donation_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="one_time"
    )
    campaign = models.CharField(
        max_length=20, choices=CAMPAIGN_CHOICES, default="offering"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Payment information
    stripe_payment_intent_id = models.CharField(max_length=64, blank=True)
    stripe_subscription_id = models.CharField(max_length=64, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)

    # Anonymous donation (no member linked)
    anonymous = models.BooleanField(default=False)
    donor_name = models.CharField(max_length=200, blank=True)
    donor_email = models.EmailField(blank=True)

    # Receipt
    receipt_sent = models.BooleanField(default=False)
    receipt_sent_at = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Timestamps
    donation_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "donations"
        verbose_name = "Donation"
        verbose_name_plural = "Donations"
        ordering = ["-donation_date"]
        indexes = [
            models.Index(fields=["tenant", "-donation_date"]),
            models.Index(fields=["member", "-donation_date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        if self.member:
            return f"${self.amount} - {self.member.full_name} - {self.campaign}"
        return f"${self.amount} - {self.campaign} - Anonymous"


class Expense(models.Model):
    """
    Represents a church expense.
    """

    CATEGORY_CHOICES = [
        ("operations", "Operations"),
        ("salaries", "Salaries"),
        ("utilities", "Utilities"),
        ("maintenance", "Maintenance"),
        ("programs", "Programs"),
        ("missions", "Missions"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant (church)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="expenses"
    )

    # Expense details
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="other"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Vendor
    vendor_name = models.CharField(max_length=200, blank=True)
    vendor_email = models.EmailField(blank=True)

    # Date
    expense_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    # Receipt
    receipt = models.FileField(upload_to="expenses/receipts/", null=True, blank=True)

    # Who created/approved
    created_by = models.ForeignKey(
        "members.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="expenses_created",
    )
    approved_by = models.ForeignKey(
        "members.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_approved",
    )

    # Notes
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses"
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ["-expense_date"]

    def __str__(self):
        return f"${self.amount} - {self.description}"


class Campaign(models.Model):
    """
    Represents a fundraising campaign.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant (church)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="campaigns"
    )

    # Campaign details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    goal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Is this a recurring campaign?
    is_recurring = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns"
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    @property
    def total_raised(self):
        return (
            self.donations.filter(status="completed").aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )

    @property
    def progress_percentage(self):
        if self.goal:
            return min(100, (self.total_raised / self.goal) * 100)
        return 0
