"""
Serializers for Education (courses) API.
"""

from rest_framework import serializers

from education.models import BlockCertificate, Course, CourseBlock, Enrollment


class CourseBlockSerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseBlock
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "courses_count",
            "created_at",
        ]

    def get_courses_count(self, obj):
        return obj.courses_count()


class CourseSerializer(serializers.ModelSerializer):
    is_standalone = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "instructor",
            "is_active",
            "capacity",
            "requires_baptized",
            "requires_married",
            "prerequisite_courses",
            "course_block",
            "order_in_block",
            "is_standalone",
            "created_at",
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = [
            "id",
            "member",
            "course",
            "status",
            "enrolled_at",
            "completed_at",
        ]
        read_only_fields = ["enrolled_at", "completed_at"]


class BlockCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockCertificate
        fields = [
            "id",
            "member",
            "course_block",
            "certificate_number",
            "issued_at",
        ]
        read_only_fields = ["certificate_number", "issued_at"]
