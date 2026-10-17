"""
Serializers for Members API.
"""

from rest_framework import serializers
from members.models import Member, Family, Tag


class PastoralNotesMixin:
    """`notes` is visible to, and writable by, only the roles allowed to see
    pastoral notes; for everyone else the key is dropped in both directions."""

    def _can_see_notes(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.can_view_pastoral_notes)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self._can_see_notes():
            data.pop("notes", None)
        return data

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        if not self._can_see_notes():
            validated.pop("notes", None)
        return validated


class HomeSiteMixin:
    def validate_home_site(self, site):
        tenant = getattr(getattr(self.context.get("request"), "user", None), "tenant", None)
        if site is not None and tenant is not None and site.tenant_id != tenant.pk:
            raise serializers.ValidationError("Sede no válida.")
        return site


class NationalIdMixin:
    """An ID may belong to only one live member of the church."""

    def validate_national_id(self, value):
        value = (value or "").strip()
        key = Member.normalize_national_id(value)
        if not key:
            return value
        request = self.context.get("request")
        tenant = getattr(getattr(request, "user", None), "tenant", None)
        if tenant is None:
            return value
        clash = Member.objects.filter(tenant=tenant, national_id_key=key)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        found = clash.first()
        if found:
            raise serializers.ValidationError(f"Esta identificación ya pertenece a {found.full_name}.")
        return value


class MemberSerializer(HomeSiteMixin, NationalIdMixin, PastoralNotesMixin, serializers.ModelSerializer):
    """
    Serializer for Member model.
    """

    full_name = serializers.ReadOnlyField()
    family_name = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "national_id",
            "date_of_birth",
            "gender",
            "marital_status",
            "is_baptized",
            "baptism_date",
            "member_status",
            "membership_date",
            "family",
            "family_name",
            "home_site",
            "address",
            "city",
            "state",
            "postal_code",
            "photo",
            "notes",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_family_name(self, obj):
        return obj.family.name if obj.family else None


class MemberCreateSerializer(HomeSiteMixin, NationalIdMixin, PastoralNotesMixin, serializers.ModelSerializer):
    """
    Serializer for creating a new Member.
    """

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "national_id",
            "date_of_birth",
            "gender",
            "marital_status",
            "is_baptized",
            "baptism_date",
            "member_status",
            "membership_date",
            "family",
            "home_site",
            "address",
            "city",
            "state",
            "postal_code",
            "notes",
            "tags",
        ]


class FamilySerializer(PastoralNotesMixin, serializers.ModelSerializer):
    """
    Serializer for Family model.
    """

    member_count = serializers.SerializerMethodField()
    members = MemberSerializer(many=True, read_only=True)

    class Meta:
        model = Family
        fields = [
            "id",
            "name",
            "head_of_family",
            "address",
            "city",
            "state",
            "postal_code",
            "home_phone",
            "notes",
            "member_count",
            "members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_member_count(self, obj):
        return obj.members.count()


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for Tag model.
    """

    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "color",
            "member_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_member_count(self, obj):
        return obj.members.count()
