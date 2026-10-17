"""
Serializers for Events API.
"""

from rest_framework import serializers

from events.models import Event, EventAttendance, EventRegistration
from tenants.models import Site


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "name", "address", "phone", "is_main", "is_active"]
        read_only_fields = fields


class EventSerializer(serializers.ModelSerializer):
    registered_count = serializers.ReadOnlyField()
    site_name = serializers.CharField(source="site.name", read_only=True, default=None)

    def validate_site(self, site):
        """Only this church's own sites."""
        tenant = getattr(getattr(self.context.get("request"), "user", None), "tenant", None)
        if site is not None and tenant is not None and site.tenant_id != tenant.pk:
            raise serializers.ValidationError("Sede no válida.")
        return site

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "event_type",
            "site",
            "site_name",
            "location",
            "start_at",
            "end_at",
            "is_active",
            "capacity",
            "requires_baptized",
            "requires_married",
            "required_courses",
            "registered_count",
            "created_at",
        ]


class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = ["id", "member", "event", "status", "registered_at"]
        read_only_fields = ["status", "registered_at"]


class EventAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventAttendance
        fields = ["id", "member", "event", "checked_in_at"]
        read_only_fields = ["checked_in_at"]
