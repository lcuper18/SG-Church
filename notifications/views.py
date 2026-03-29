"""
API views for notifications.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Notification


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notifications.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only notifications for the current user's tenant."""
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Notification.objects.none()
        return Notification.objects.filter(tenant=tenant, user=self.request.user)

    def list(self, request, *args, **kwargs):
        """List all notifications for the current user."""
        queryset = self.get_queryset()

        # Filter by read status
        is_read = request.query_params.get("is_read")
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == "true")

        # Limit to 50 most recent
        queryset = queryset[:50]

        # Get unread count
        unread_count = self.get_queryset().filter(is_read=False).count()

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "notifications": serializer.data,
                "unread_count": unread_count,
            }
        )

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({"status": "marked as read"})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user."""
        notifications = self.get_queryset().filter(is_read=False)
        count = notifications.count()
        notifications.update(is_read=True, read_at=timezone.now())
        return Response(
            {
                "status": "all marked as read",
                "count": count,
            }
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get the count of unread notifications."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})
