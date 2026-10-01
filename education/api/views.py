"""
Views for Education (courses) API.
"""

from rest_framework import filters, viewsets
from rest_framework.exceptions import ValidationError

from core.permissions import CanManageEducation, CanManageMembers
from education.models import BlockCertificate, Course, CourseBlock, Enrollment

from .serializers import (
    BlockCertificateSerializer,
    CourseBlockSerializer,
    CourseSerializer,
    EnrollmentSerializer,
)


class CourseBlockViewSet(viewsets.ModelViewSet):
    """ViewSet for managing course blocks."""

    serializer_class = CourseBlockSerializer
    permission_classes = [CanManageEducation]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return CourseBlock.objects.all()
        if hasattr(user, "tenant") and user.tenant:
            return CourseBlock.objects.filter(tenant=user.tenant)
        return CourseBlock.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing courses."""

    serializer_class = CourseSerializer
    permission_classes = [CanManageEducation]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "created_at"]
    ordering = ["title"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Course.objects.all()
        if hasattr(user, "tenant") and user.tenant:
            return Course.objects.filter(tenant=user.tenant)
        return Course.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, "tenant") and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()


class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing enrollments. Creating/deleting an enrollment
    follows CanManageMembers (day-to-day member management); only
    CanManageEducation may update one (i.e. mark it completed, which
    certifies the member finished the course)."""

    serializer_class = EnrollmentSerializer
    ordering = ["-enrolled_at"]

    def get_permissions(self):
        if self.action in ["partial_update", "update"]:
            return [CanManageEducation()]
        return [CanManageMembers()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Enrollment.objects.all()
        if hasattr(user, "tenant") and user.tenant:
            return Enrollment.objects.filter(tenant=user.tenant)
        return Enrollment.objects.none()

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, "tenant", None)
        course = serializer.validated_data["course"]
        member = serializer.validated_data["member"]

        allowed, reason = course.can_enroll(member)
        if not allowed:
            raise ValidationError(reason)

        serializer.save(tenant=tenant)

    def perform_update(self, serializer):
        """Route a status="completed" update through mark_completed() so
        the block-certificate check actually runs, instead of letting the
        serializer blindly overwrite the field."""
        if serializer.validated_data.get("status") == "completed":
            serializer.instance.mark_completed()
        else:
            serializer.save()

    def perform_destroy(self, instance):
        """Drop rather than delete, mirroring education.views.enrollment_delete
        — preserves history and the prerequisite-completion trail."""
        instance.status = "dropped"
        instance.save(update_fields=["status"])


class BlockCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only: certificates are issued automatically, not created via API."""

    serializer_class = BlockCertificateSerializer
    permission_classes = [CanManageMembers]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return BlockCertificate.objects.all()
        if hasattr(user, "tenant") and user.tenant:
            return BlockCertificate.objects.filter(tenant=user.tenant)
        return BlockCertificate.objects.none()
