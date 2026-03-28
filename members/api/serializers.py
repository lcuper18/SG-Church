"""
Serializers for Members API.
"""

from rest_framework import serializers
from members.models import Member, Family


class MemberSerializer(serializers.ModelSerializer):
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
            "date_of_birth",
            "gender",
            "marital_status",
            "member_status",
            "membership_date",
            "family",
            "family_name",
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


class MemberCreateSerializer(serializers.ModelSerializer):
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
            "date_of_birth",
            "gender",
            "marital_status",
            "member_status",
            "membership_date",
            "family",
            "address",
            "city",
            "state",
            "postal_code",
            "notes",
            "tags",
        ]


class FamilySerializer(serializers.ModelSerializer):
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
