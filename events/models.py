"""
Event models for SG Church.
"""

import uuid

from django.db import models
from django.utils import timezone


class Event(models.Model):
    """A church event or special activity members can register for."""

    TYPE_CHOICES = [
        ("service", "Servicio"),
        ("meeting", "Reunión"),
        ("retreat", "Retiro"),
        ("conference", "Conferencia"),
        ("camp", "Campamento"),
        ("special", "Actividad especial"),
        ("other", "Otro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="events"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")
    location = models.CharField(max_length=255, blank=True)

    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)

    # Eligibility requirements (same idea as education.Course)
    requires_baptized = models.BooleanField(default=False)
    requires_married = models.BooleanField(default=False)
    required_courses = models.ManyToManyField(
        "education.Course", blank=True, related_name="required_for_events"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events"
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["tenant", "start_at"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_past(self):
        return (self.end_at or self.start_at) < timezone.now()

    @property
    def attendance_open(self):
        """Attendance can be taken from the day of the event onwards, not before."""
        return timezone.localdate() >= timezone.localtime(self.start_at).date()

    @property
    def attended_count(self):
        return self.attendances.count()

    @property
    def registered_count(self):
        return self.registrations.filter(status="registered").count()

    def meets_requirements(self, member):
        """Return (True, "") if `member` satisfies the eligibility requirements
        (baptism, marriage, completed courses), else (False, reason). Says
        nothing about dates, capacity or existing registration."""
        if self.requires_baptized and not member.is_baptized:
            return False, "Este evento requiere que el miembro esté bautizado."
        if self.requires_married and member.marital_status != "married":
            return False, "Este evento requiere que el miembro esté casado/a."
        missing = self.required_courses.exclude(
            enrollments__member=member, enrollments__status="completed"
        )
        if missing.exists():
            names = ", ".join(missing.values_list("title", flat=True))
            return False, f"Debe completar primero: {names}."
        return True, ""

    def can_register(self, member):
        """Return (True, "") if `member` may register now, else (False, reason)."""
        if not self.is_active:
            return False, "Este evento no está disponible."
        if self.is_past:
            return False, "Este evento ya finalizó."
        eligible, reason = self.meets_requirements(member)
        if not eligible:
            return False, reason
        if self.capacity is not None and self.registered_count >= self.capacity:
            return False, "Este evento alcanzó su capacidad máxima."
        if self.registrations.filter(member=member, status="registered").exists():
            return False, "El miembro ya está inscrito en este evento."
        return True, ""


class EventRegistration(models.Model):
    """A member's registration for an event."""

    STATUS_CHOICES = [
        ("registered", "Inscrito"),
        ("cancelled", "Cancelado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="event_registrations"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="event_registrations"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="registered")
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_registrations"
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"
        ordering = ["-registered_at"]
        unique_together = ["member", "event"]

    def __str__(self):
        return f"{self.member.full_name} - {self.event.title} ({self.status})"


class EventAttendance(models.Model):
    """A member who attended an event. A row means "attended"; unmarking
    deletes it. Any member of the church can be marked, registered or not."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="event_attendances"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.CASCADE, related_name="event_attendances"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="attendances"
    )
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_attendances"
        verbose_name = "Event Attendance"
        verbose_name_plural = "Event Attendances"
        ordering = ["-checked_in_at"]
        unique_together = ["member", "event"]
        indexes = [models.Index(fields=["tenant", "event"])]

    def __str__(self):
        return f"{self.member.full_name} @ {self.event.title}"
