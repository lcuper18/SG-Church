"""
Views for Finance API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.utils import timezone

from finance.models import Donation, Expense, Campaign
from .serializers import (
    DonationSerializer,
    DonationCreateSerializer,
    ExpenseSerializer,
    ExpenseCreateSerializer,
    CampaignSerializer,
    CampaignCreateSerializer,
)


class DonationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing donations.

    list: Get all donations
    create: Create a new donation
    retrieve: Get a specific donation
    update: Update a donation
    destroy: Delete a donation
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "member__first_name",
        "member__last_name",
        "donor_name",
        "donor_email",
    ]
    ordering_fields = ["donation_date", "amount", "created_at"]
    ordering = ["-donation_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return DonationCreateSerializer
        return DonationSerializer

    def get_queryset(self):
        """Filter donations by tenant."""
        user = self.request.user

        if user.is_superuser:
            return Donation.objects.all()

        if hasattr(user, "tenant") and user.tenant:
            return Donation.objects.filter(tenant=user.tenant)

        return Donation.objects.none()

    def perform_create(self, serializer):
        """Set tenant from user when creating donation."""
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get donation statistics."""
        queryset = self.get_queryset()

        # Get date range from query params
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(donation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(donation_date__lte=end_date)

        # Calculate totals by campaign
        by_campaign = (
            queryset.filter(status="completed")
            .values("campaign")
            .annotate(total=Sum("amount"), count=Count("id"))
        )

        return Response(
            {
                "total_raised": queryset.filter(status="completed").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0,
                "total_donations": queryset.filter(status="completed").count(),
                "pending_donations": queryset.filter(status="pending").count(),
                "by_campaign": list(by_campaign),
            }
        )

    @action(detail=False, methods=["get"])
    def by_member(self, request):
        """Get donations grouped by member."""
        member_id = request.query_params.get("member_id")

        if not member_id:
            return Response(
                {"error": "member_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(member_id=member_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing expenses.

    list: Get all expenses
    create: Create a new expense
    retrieve: Get a specific expense
    update: Update an expense
    destroy: Delete an expense
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "vendor_name", "vendor_email"]
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def get_queryset(self):
        """Filter expenses by tenant."""
        user = self.request.user

        if user.is_superuser:
            return Expense.objects.all()

        if hasattr(user, "tenant") and user.tenant:
            return Expense.objects.filter(tenant=user.tenant)

        return Expense.objects.none()

    def perform_create(self, serializer):
        """Set tenant and created_by from user when creating expense."""
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(
                tenant=self.request.user.tenant, created_by=self.request.user
            )
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get expense statistics."""
        queryset = self.get_queryset()

        # Get date range from query params
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(expense_date__lte=end_date)

        # Calculate totals by category
        by_category = queryset.values("category").annotate(
            total=Sum("amount"), count=Count("id")
        )

        return Response(
            {
                "total_expenses": queryset.aggregate(total=Sum("amount"))["total"] or 0,
                "pending": queryset.filter(status="pending").count(),
                "approved": queryset.filter(status="approved").count(),
                "paid": queryset.filter(status="paid").count(),
                "by_category": list(by_category),
            }
        )


class CampaignViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing campaigns.

    list: Get all campaigns
    create: Create a new campaign
    retrieve: Get a specific campaign
    update: Update a campaign
    destroy: Delete a campaign
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["start_date", "end_date", "goal", "created_at"]
    ordering = ["-start_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return CampaignCreateSerializer
        return CampaignSerializer

    def get_queryset(self):
        """Filter campaigns by tenant."""
        user = self.request.user

        if user.is_superuser:
            return Campaign.objects.all()

        if hasattr(user, "tenant") and user.tenant:
            return Campaign.objects.filter(tenant=user.tenant)

        return Campaign.objects.none()

    def perform_create(self, serializer):
        """Set tenant from user when creating campaign."""
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get active campaigns."""
        queryset = self.get_queryset().filter(status="active")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
