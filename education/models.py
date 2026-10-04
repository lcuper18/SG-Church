"""
Education (courses) models for SG Church.
"""

import uuid

from django.db import models
from django.utils import timezone


class CourseBlock(models.Model):
    """A named group of courses. Completing every course in a block earns
    the member a BlockCertificate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="course_blocks"
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "course_blocks"
        verbose_name = "Course Block"
        verbose_name_plural = "Course Blocks"
        ordering = ["name"]
        unique_together = ["tenant", "name"]

    def __str__(self):
        return self.name

    def courses_count(self):
        return self.courses.count()

    def check_and_issue_certificate(self, member):
        """If `member` has completed every active course in this block,
        create (or return the existing) BlockCertificate."""
        existing = self.certificates.filter(member=member).first()
        if existing:
            return existing

        block_course_ids = set(
            self.courses.filter(is_active=True).values_list("id", flat=True)
        )
        if not block_course_ids:
            return None

        completed_ids = set(
            Enrollment.objects.filter(
                member=member, course_id__in=block_course_ids, status="completed"
            ).values_list("course_id", flat=True)
        )
        if block_course_ids <= completed_ids:
            return BlockCertificate.objects.create(
                tenant=self.tenant, member=member, course_block=self
            )
        return None


class Course(models.Model):
    """A single course. May stand alone (course_block is None) or belong to
    one CourseBlock."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="courses"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        "members.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses_taught",
    )

    is_active = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    # Eligibility requirements
    requires_baptized = models.BooleanField(default=False)
    requires_married = models.BooleanField(default=False)

    # Courses that must be completed before enrolling in this one.
    prerequisite_courses = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="unlocks_courses"
    )

    # A course belongs to at most one block. course_block=None means it's
    # an independent course.
    course_block = models.ForeignKey(
        CourseBlock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    order_in_block = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text="Display order within the block (ignored for independent courses)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "courses"
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ["course_block__name", "order_in_block", "title"]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["course_block"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_standalone(self):
        return self.course_block_id is None

    def can_enroll(self, member):
        """Return (True, "") if `member` may enroll now, else (False, reason)."""
        if not self.is_active:
            return False, "Este curso no está disponible."
        if self.requires_baptized and not member.is_baptized:
            return False, "Este curso requiere que el miembro esté bautizado."
        if self.requires_married and member.marital_status != "married":
            return False, "Este curso requiere que el miembro esté casado/a."
        if self.capacity is not None:
            active_count = self.enrollments.filter(
                status__in=["enrolled", "completed"]
            ).count()
            if active_count >= self.capacity:
                return False, "Este curso alcanzó su capacidad máxima."
        missing = self.prerequisite_courses.exclude(
            enrollments__member=member, enrollments__status="completed"
        )
        if missing.exists():
            names = ", ".join(missing.values_list("title", flat=True))
            return False, f"Debe completar primero: {names}."
        if self.enrollments.filter(member=member).exclude(status="dropped").exists():
            return False, "El miembro ya está inscrito en este curso."
        return True, ""


class Enrollment(models.Model):
    """A member's enrollment in a course."""

    STATUS_CHOICES = [
        ("enrolled", "Inscrito"),
        ("completed", "Completado"),
        ("dropped", "Retirado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="enrollments"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="enrolled")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "enrollments"
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        ordering = ["-enrolled_at"]
        unique_together = ["member", "course"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["member", "status"]),
        ]

    def __str__(self):
        return f"{self.member.full_name} - {self.course.title} ({self.status})"

    def mark_completed(self):
        """Mark this enrollment completed and, if it finishes a block,
        issue the BlockCertificate. Returns the BlockCertificate if one
        was (newly or previously) issued, else None."""
        if self.status != "completed":
            self.status = "completed"
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at"])

        if self.course.course_block_id is None:
            return None
        return self.course.course_block.check_and_issue_certificate(self.member)


class BlockCertificate(models.Model):
    """A persisted record that a member completed every course in a block."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="block_certificates"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="block_certificates"
    )
    course_block = models.ForeignKey(
        CourseBlock, on_delete=models.CASCADE, related_name="certificates"
    )

    certificate_number = models.CharField(max_length=40, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "block_certificates"
        verbose_name = "Block Certificate"
        verbose_name_plural = "Block Certificates"
        ordering = ["-issued_at"]
        unique_together = ["member", "course_block"]

    def __str__(self):
        return f"{self.certificate_number} - {self.member.full_name} - {self.course_block.name}"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self._generate_number()
        super().save(*args, **kwargs)

    def _generate_number(self):
        year = timezone.now().year
        return f"CERT-{year}-{uuid.uuid4().hex[:8].upper()}"
