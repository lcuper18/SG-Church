"""
Serializers for Events API.
"""

from rest_framework import serializers

from events.models import Event, EventRegistration


class EventSerializer(serializers.ModelSerializer):
    registered_count = serializers.ReadOnlyField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "event_type",
            "location",
            "start_at",
            "end_at",
            "is_active",
            "capacity",
            "registered_count",
            "created_at",
        ]


class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = ["id", "member", "event", "status", "registered_at"]
        read_only_fields = ["status", "registered_at"]
