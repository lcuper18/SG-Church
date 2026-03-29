"""
Serializers for notifications API.
"""

from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    icon = serializers.CharField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "icon",
            "link",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields
