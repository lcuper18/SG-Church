"""
Serializers for Finance API.
"""

from rest_framework import serializers
from finance.models import Donation, Expense, Campaign


class DonationSerializer(serializers.ModelSerializer):
    """
    Serializer for Donation model.
    """

    member_name = serializers.SerializerMethodField()
    campaign_display = serializers.CharField(
        source="get_campaign_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    type_display = serializers.CharField(
        source="get_donation_type_display", read_only=True
    )

    class Meta:
        model = Donation
        fields = [
            "id",
            "member",
            "member_name",
            "amount",
            "currency",
            "donation_type",
            "type_display",
            "campaign",
            "campaign_display",
            "status",
            "status_display",
            "stripe_payment_intent_id",
            "stripe_subscription_id",
            "payment_method",
            "anonymous",
            "donor_name",
            "donor_email",
            "receipt_sent",
            "receipt_sent_at",
            "notes",
            "donation_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "stripe_payment_intent_id",
            "stripe_subscription_id",
            "receipt_sent",
            "receipt_sent_at",
            "donation_date",
            "created_at",
            "updated_at",
        ]

    def get_member_name(self, obj):
        if obj.member:
            return obj.member.full_name
        if obj.anonymous:
            return "Anonymous"
        return obj.donor_name


class DonationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Donation.
    """

    class Meta:
        model = Donation
        fields = [
            "member",
            "amount",
            "currency",
            "donation_type",
            "campaign",
            "anonymous",
            "donor_name",
            "donor_email",
            "payment_method",
            "stripe_payment_intent_id",
            "stripe_subscription_id",
            "notes",
        ]


class ExpenseSerializer(serializers.ModelSerializer):
    """
    Serializer for Expense model.
    """

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "description",
            "amount",
            "category",
            "category_display",
            "status",
            "status_display",
            "vendor_name",
            "vendor_email",
            "expense_date",
            "due_date",
            "receipt",
            "created_by",
            "created_by_name",
            "approved_by",
            "approved_by_name",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "approved_by",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else None


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Expense.
    """

    class Meta:
        model = Expense
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


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for Campaign model.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_raised = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    progress_percentage = serializers.FloatField(read_only=True)
    donation_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "description",
            "goal",
            "start_date",
            "end_date",
            "status",
            "status_display",
            "is_recurring",
            "total_raised",
            "progress_percentage",
            "donation_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_donation_count(self, obj):
        return obj.donations.filter(status="completed").count()


class CampaignCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Campaign.
    """

    class Meta:
        model = Campaign
        fields = [
            "name",
            "description",
            "goal",
            "start_date",
            "end_date",
            "status",
            "is_recurring",
        ]
