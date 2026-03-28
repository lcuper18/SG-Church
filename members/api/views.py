"""
Views for Members API.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from members.models import Member, Family
from .serializers import MemberSerializer, MemberCreateSerializer, FamilySerializer


class MemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing members.

    list: Get all members
    create: Create a new member
    retrieve: Get a specific member
    update: Update a member
    destroy: Delete a member
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = ["last_name", "first_name", "created_at"]
    ordering = ["last_name", "first_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return MemberCreateSerializer
        return MemberSerializer

    def get_queryset(self):
        """
        Filter members by tenant if user is authenticated.
        """
        user = self.request.user

        # If user is superuser, return all
        if user.is_superuser:
            return Member.objects.all()

        # Filter by tenant if user has one
        if hasattr(user, "tenant") and user.tenant:
            return Member.objects.filter(tenant=user.tenant)

        # Return empty queryset
        return Member.objects.none()

    def perform_create(self, serializer):
        """Set tenant from user when creating member."""
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get member statistics."""
        queryset = self.get_queryset()

        return Response(
            {
                "total": queryset.count(),
                "members": queryset.filter(member_status="member").count(),
                "visitors": queryset.filter(member_status="visitor").count(),
                "attendees": queryset.filter(member_status="attendee").count(),
                "inactive": queryset.filter(member_status="inactive").count(),
            }
        )

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search members by query."""
        query = request.query_params.get("q", "")

        if not query:
            return Response({"members": []})

        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )[:10]

        serializer = self.get_serializer(queryset, many=True)
        return Response({"members": serializer.data})


class FamilyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing families.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FamilySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "head_of_family__first_name", "head_of_family__last_name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        """Filter families by tenant."""
        user = self.request.user

        if user.is_superuser:
            return Family.objects.all()

        if hasattr(user, "tenant") and user.tenant:
            return Family.objects.filter(tenant=user.tenant)

        return Family.objects.none()

    def perform_create(self, serializer):
        """Set tenant from user when creating family."""
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()
