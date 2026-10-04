"""
Views for Events API.
"""

from rest_framework import filters, viewsets
from rest_framework.exceptions import ValidationError

from core.permissions import CanManageMembers
from events.models import Event, EventRegistration

from .serializers import EventRegistrationSerializer, EventSerializer


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing events."""

    serializer_class = EventSerializer
    permission_classes = [CanManageMembers]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "location"]
    ordering_fields = ["start_at", "title"]
    ordering = ["start_at"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Event.objects.all()
        if hasattr(user, "tenant") and user.tenant:
            return Event.objects.filter(tenant=user.tenant)
        return Event.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()


class EventRegistrationViewSet(viewsets.ModelViewSet):
    """ViewSet for event registrations. Deleting cancels (keeps the row)."""

    serializer_class = EventRegistrationSerializer
    permission_classes = [CanManageMembers]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return EventRegistration.objects.all()
        if hasattr(user, "tenant") and user.tenant:
            return EventRegistration.objects.filter(tenant=user.tenant)
        return EventRegistration.objects.none()

    def perform_create(self, serializer):
        event = serializer.validated_data["event"]
        member = serializer.validated_data["member"]
        allowed, reason = event.can_register(member)
        if not allowed:
            raise ValidationError(reason)
        serializer.save(tenant=self.request.user.tenant)

    def perform_destroy(self, instance):
        instance.status = "cancelled"
        instance.save(update_fields=["status"])
