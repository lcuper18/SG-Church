"""
Event and registration views.
"""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import ManageMembersRequiredMixin
from education.models import Course
from members.models import Member

from .models import Event, EventAttendance, EventRegistration

EVENT_FIELDS = [
    "title",
    "description",
    "event_type",
    "location",
    "start_at",
    "end_at",
    "capacity",
    "requires_baptized",
    "requires_married",
    "required_courses",
    "is_active",
]


class EventListView(LoginRequiredMixin, ListView):
    """List the tenant's events, optionally filtered by type."""

    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        queryset = Event.objects.filter(tenant=tenant)
        event_type = self.request.GET.get("type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["type_choices"] = Event.TYPE_CHOICES
        return context


event_list = EventListView.as_view()


class EventDetailView(LoginRequiredMixin, DetailView):
    """Event detail with its registrations."""

    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        return Event.objects.filter(tenant=tenant)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)
        event = self.object

        registrations = event.registrations.filter(status="registered").select_related(
            "member"
        )
        context["registrations"] = registrations
        attended_ids = set(event.attendances.values_list("member_id", flat=True))
        registered_ids = set(registrations.values_list("member_id", flat=True))
        context["attended_count"] = len(attended_ids)
        context["no_show_count"] = len(registered_ids - attended_ids)
        context["attended_ids"] = attended_ids
        if tenant:
            context["registrable_members"] = Member.objects.filter(
                tenant=tenant
            ).exclude(id__in=registrations.values_list("member_id", flat=True))
        return context


event_detail = EventDetailView.as_view()


class EventCreateView(ManageMembersRequiredMixin, CreateView):
    """Create a new event."""

    model = Event
    template_name = "events/event_form.html"
    fields = EVENT_FIELDS

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["required_courses"].queryset = Course.objects.filter(
                tenant=tenant
            )
        return form

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("event_detail", kwargs={"pk": self.object.pk})


event_create = EventCreateView.as_view()


class EventUpdateView(ManageMembersRequiredMixin, UpdateView):
    """Update an existing event."""

    model = Event
    template_name = "events/event_form.html"
    fields = EVENT_FIELDS

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        return Event.objects.filter(tenant=tenant)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["required_courses"].queryset = Course.objects.filter(
                tenant=tenant
            )
        return form

    def get_success_url(self):
        return reverse("event_detail", kwargs={"pk": self.object.pk})


event_update = EventUpdateView.as_view()


class EventDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete an event."""

    model = Event
    template_name = "events/event_confirm_delete.html"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        return Event.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("event_list")


event_delete = EventDeleteView.as_view()


class RegistrationCreateView(ManageMembersRequiredMixin, View):
    """Register a member for an event (POST only)."""

    def post(self, request, event_pk):
        tenant = getattr(request.user, "tenant", None)
        event = get_object_or_404(Event, pk=event_pk, tenant=tenant)
        member = get_object_or_404(Member, pk=request.POST.get("member"), tenant=tenant)

        allowed, reason = event.can_register(member)
        if not allowed:
            messages.error(request, reason)
            return redirect("event_detail", pk=event.pk)

        registration, created = EventRegistration.objects.get_or_create(
            tenant=tenant, member=member, event=event
        )
        if not created and registration.status == "cancelled":
            registration.status = "registered"
            registration.save(update_fields=["status"])

        messages.success(request, f"{member.full_name} fue inscrito/a en el evento.")
        return redirect("event_detail", pk=event.pk)


registration_create = RegistrationCreateView.as_view()


class RegistrationCancelView(ManageMembersRequiredMixin, View):
    """Cancel a registration (POST only) - flips status, keeps the row."""

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        registration = get_object_or_404(EventRegistration, pk=pk, tenant=tenant)
        registration.status = "cancelled"
        registration.save(update_fields=["status"])
        messages.success(request, "Se canceló la inscripción.")
        return redirect("event_detail", pk=registration.event.pk)


registration_cancel = RegistrationCancelView.as_view()


# ============================================================
# ATTENDANCE
# ============================================================


class AttendanceView(ManageMembersRequiredMixin, View):
    """Checklist to mark who attended an event (any member, registered or not)."""

    template_name = "events/attendance.html"

    def _event(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        return get_object_or_404(Event, pk=pk, tenant=tenant), tenant

    def get(self, request, pk):
        event, tenant = self._event(request, pk)
        query = request.GET.get("q", "").strip()
        only_registered = request.GET.get("filter") == "registered"

        registered_ids = set(
            event.registrations.filter(status="registered").values_list(
                "member_id", flat=True
            )
        )
        members = Member.objects.filter(tenant=tenant)
        if query:
            members = members.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        if only_registered:
            members = members.filter(id__in=registered_ids)

        return render(
            request,
            self.template_name,
            {
                "event": event,
                "members": members.order_by("last_name", "first_name"),
                "registered_ids": registered_ids,
                "present_ids": set(event.attendances.values_list("member_id", flat=True)),
                "query": query,
                "only_registered": only_registered,
            },
        )

    def post(self, request, pk):
        event, tenant = self._event(request, pk)
        if not event.attendance_open:
            messages.error(request, "La asistencia se puede tomar a partir del día del evento.")
            return redirect("event_detail", pk=event.pk)

        # Only touch the members that were on screen: a search-filtered list
        # must not un-mark the ones that were hidden.
        shown = set(
            Member.objects.filter(
                tenant=tenant, id__in=request.POST.getlist("shown")
            ).values_list("id", flat=True)
        )
        checked = set(request.POST.getlist("present"))
        present = {member_id for member_id in shown if str(member_id) in checked}

        existing = set(event.attendances.values_list("member_id", flat=True))
        EventAttendance.objects.bulk_create(
            [
                EventAttendance(tenant=tenant, member_id=member_id, event=event)
                for member_id in present - existing
            ]
        )
        event.attendances.filter(member_id__in=(shown - present)).delete()

        messages.success(request, f"Asistencia guardada: {event.attended_count} presentes.")
        return redirect("event_detail", pk=event.pk)


event_attendance = AttendanceView.as_view()


class AttendanceReportView(ManageMembersRequiredMixin, View):
    """Attendance totals per event and per member over a date range."""

    template_name = "events/attendance_report.html"

    @staticmethod
    def _parse(value, default):
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return default

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        today = timezone.localdate()
        start = self._parse(request.GET.get("start"), today - timedelta(days=90))
        end = self._parse(request.GET.get("end"), today)
        event_type = request.GET.get("type", "")

        events = Event.objects.filter(
            tenant=tenant, start_at__date__gte=start, start_at__date__lte=end
        )
        if event_type:
            events = events.filter(event_type=event_type)

        event_rows = events.annotate(
            registered=Count(
                "registrations", filter=Q(registrations__status="registered"), distinct=True
            ),
            attended=Count("attendances", distinct=True),
        ).order_by("-start_at")
        total_events = events.count()

        member_rows = (
            Member.objects.filter(tenant=tenant, event_attendances__event__in=events)
            .annotate(
                attended=Count("event_attendances", distinct=True),
                last_attended=Max("event_attendances__event__start_at"),
            )
            .order_by("-attended", "last_name", "first_name")
        )
        page = Paginator(member_rows, 50).get_page(request.GET.get("page"))
        for row in page:
            row.percent = round(row.attended * 100 / total_events) if total_events else 0

        return render(
            request,
            self.template_name,
            {
                "start": start,
                "end": end,
                "event_type": event_type,
                "type_choices": Event.TYPE_CHOICES,
                "event_rows": event_rows,
                "total_events": total_events,
                "total_attendances": sum(r.attended for r in event_rows),
                "page": page,
            },
        )


attendance_report = AttendanceReportView.as_view()
