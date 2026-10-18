"""
Event and registration views.
"""

import uuid
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Case, Count, DateTimeField, F, IntegerField, Max, Q, Value, When
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

from core.exports import csv_response, export_filename
from core.mixins import ManageMembersRequiredMixin
from members.search import search_members
from emails import notify
from education.models import Course
from members.models import Member
from tenants.models import Site

from . import recurrence
from .forms import EVENT_FIELDS, WEEKDAY_CHOICES, EventForm
from .models import Event, EventAttendance, EventRegistration

class EventFormMixin:
    """Shared by create/update: the course and site pickers, limited to this church."""

    form_class = EventForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = getattr(self.request.user, "tenant", None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["weekday_choices"] = [(str(n), label) for n, label in WEEKDAY_CHOICES]
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["required_courses"].queryset = Course.objects.filter(tenant=tenant)
            sites = Site.objects.filter(tenant=tenant, is_active=True)
            if self.object and self.object.site_id:
                sites = Site.objects.filter(tenant=tenant).filter(
                    Q(is_active=True) | Q(pk=self.object.site_id)
                )
            form.fields["site"].queryset = sites
            form.fields["site"].required = False  # blank = the main site
            form.fields["site"].empty_label = None
            if self.object is None:
                form.initial.setdefault("site", tenant.main_site().pk)
            if not tenant.uses_sites:
                del form.fields["site"]  # one site: nothing to choose
        return form


def _uuid_or_none(value):
    try:
        return uuid.UUID(str(value)) if value else None
    except ValueError:
        return None


class EventListView(LoginRequiredMixin, ListView):
    """List the tenant's events, optionally filtered by type."""

    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        queryset = (
            Event.objects.filter(tenant=tenant)
            .annotate(
                registered_total=Count(
                    "registrations", filter=Q(registrations__status="registered")
                ),
                # Upcoming events first (soonest first), then past ones (latest
                # first), so page 1 is what people look for. Meta.ordering is
                # ignored once the query groups, hence explicit.
                is_past_bucket=Case(
                    When(start_at__gte=timezone.now(), then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                upcoming_at=Case(
                    When(start_at__gte=timezone.now(), then=F("start_at")),
                    output_field=DateTimeField(),
                ),
            )
            .prefetch_related("required_courses")
            .order_by("is_past_bucket", F("upcoming_at").asc(nulls_last=True), "-start_at")
        )
        event_type = self.request.GET.get("type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        site_id = _uuid_or_none(self.request.GET.get("site"))
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        return queryset.select_related("site")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["type_choices"] = Event.TYPE_CHOICES
        tenant = getattr(self.request.user, "tenant", None)
        if tenant and tenant.uses_sites:
            context["site_choices"] = Site.objects.filter(tenant=tenant)
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
        return context


event_detail = EventDetailView.as_view()


class EventCreateView(EventFormMixin, ManageMembersRequiredMixin, CreateView):
    """Create a new event."""

    model = Event
    template_name = "events/event_form.html"

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        if form.rule:
            return self._create_series(form, tenant)
        return super().form_valid(form)

    def _create_series(self, form, tenant):
        """"Repetir": one event per date, linked as a series."""
        data = form.cleaned_data
        plain = {
            name: data[name]
            for name in ("title", "description", "event_type", "location", "capacity",
                         "requires_baptized", "requires_married", "is_active")
        }
        try:
            series, events = recurrence.create_series(
                tenant=tenant, user=self.request.user, fields=plain,
                courses=data.get("required_courses") or [], site=form.instance.site or tenant.main_site(),
                start_at=data["start_at"], end_at=data.get("end_at"),
                weekdays=form.rule["weekdays"], until_date=form.rule["until_date"], weeks=form.rule["weeks"],
            )
        except recurrence.RecurrenceError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        self.object = events[0]
        messages.success(
            self.request,
            f"Se crearon {len(events)} eventos «{events[0].title}» "
            f"({', '.join(series.weekday_names)}). Puedes editar o cancelar cada uno por separado.",
        )
        return redirect("event_list")

    def get_success_url(self):
        return reverse("event_detail", kwargs={"pk": self.object.pk})


event_create = EventCreateView.as_view()


class EventUpdateView(EventFormMixin, ManageMembersRequiredMixin, UpdateView):
    """Update an existing event."""

    model = Event
    template_name = "events/event_form.html"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        return Event.objects.filter(tenant=tenant)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.object.series_id and form.cleaned_data.get("edit_scope") == "following":
            others = recurrence.update_following(
                self.object, set(form.changed_data), courses=form.cleaned_data.get("required_courses")
            )
            if others:
                messages.success(self.request, f"También se actualizaron los {others} eventos siguientes de la serie.")
        return response

    def get_success_url(self):
        return reverse("event_detail", kwargs={"pk": self.object.pk})


event_update = EventUpdateView.as_view()


class EventCancelView(ManageMembersRequiredMixin, View):
    """Cancel an event (it is only deactivated, so it can be switched back on) or,
    for a series, it and the following ones; optionally tell the people registered."""

    template_name = "events/event_cancel.html"

    def _event(self, request, pk):
        return get_object_or_404(Event, pk=pk, tenant=request.user.tenant)

    def get(self, request, pk):
        return render(request, self.template_name, {"event": self._event(request, pk)})

    def post(self, request, pk):
        event = self._event(request, pk)
        scope = "following" if request.POST.get("scope") == "following" and event.series_id else "this"
        cancelled = recurrence.cancel(event, scope=scope)
        told = 0
        if request.POST.get("notify"):
            told = sum(notify.event_cancelled(e, request) for e in cancelled)
        text = f"{len(cancelled)} evento(s) cancelado(s)."
        if request.POST.get("notify"):
            text += f" Se avisó a {told} persona(s) inscrita(s)."
        messages.success(request, text)
        return redirect("event_detail", pk=event.pk)


event_cancel = EventCancelView.as_view()


class EventDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete an event."""

    model = Event
    template_name = "events/event_confirm_delete.html"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Event.objects.none()
        return Event.objects.filter(tenant=tenant)

    def form_valid(self, form):
        scope = "following" if self.request.POST.get("scope") == "following" and self.object.series_id else "this"
        count = recurrence.delete(self.object, scope=scope)
        messages.success(self.request, f"{count} evento(s) enviado(s) a la papelera.")
        return redirect(self.get_success_url())

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

        notify.event_registration(registration, request)
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
            members = search_members(members, query)
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
                "uses_sites": tenant.uses_sites,
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

        # Visitors who are not members: a head-count (blank = leave as it was).
        guests = request.POST.get("guest_count", "").strip()
        if guests.isdigit():
            event.guest_count = min(int(guests), 100000)
            event.save(update_fields=["guest_count"])

        messages.success(request, f"Asistencia guardada: {event.attended_count} presentes.")
        return redirect("event_detail", pk=event.pk)


event_attendance = AttendanceView.as_view()


def _parse_date(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def attendance_report_data(request):
    """Events in the requested range with registered/attended counts, the members
    who attended them and a per-site summary (shared by the report page and its
    CSV export). Filters: `start`, `end`, `type`, `site`."""
    tenant = getattr(request.user, "tenant", None)
    today = timezone.localdate()
    start = _parse_date(request.GET.get("start"), today - timedelta(days=90))
    end = _parse_date(request.GET.get("end"), today)
    event_type = request.GET.get("type", "")
    site_id = _uuid_or_none(request.GET.get("site"))

    events = Event.objects.filter(
        tenant=tenant, start_at__date__gte=start, start_at__date__lte=end
    )
    if event_type:
        events = events.filter(event_type=event_type)
    if site_id:
        events = events.filter(site_id=site_id)

    event_rows = list(
        events.select_related("site")
        .annotate(
            registered=Count(
                "registrations", filter=Q(registrations__status="registered"), distinct=True
            ),
            attended=Count("attendances", distinct=True),
        )
        .order_by("-start_at")
    )

    member_rows = (
        Member.objects.filter(tenant=tenant, event_attendances__event__in=events)
        .annotate(
            attended=Count("event_attendances", distinct=True),
            last_attended=Max("event_attendances__event__start_at"),
        )
        .order_by("-attended", "last_name", "first_name")
    )
    return {
        "start": start,
        "end": end,
        "event_type": event_type,
        "site_id": str(site_id) if site_id else "",
        "event_rows": event_rows,
        "total_events": len(event_rows),
        "member_rows": member_rows,
        "site_summary": site_summary(events, event_rows),
    }


def site_summary(events, event_rows):
    """One row per site that held events in the range: events, registered, members
    present, visitors, total people, average per event, and members present whose
    home site is a different one."""
    away = {
        row["event__site_id"]: row["n"]
        for row in EventAttendance.objects.filter(event__in=events, member__home_site__isnull=False)
        .exclude(member__home_site=F("event__site"))
        .values("event__site_id")
        .annotate(n=Count("id"))
    }
    summary = {}
    for event in event_rows:
        row = summary.setdefault(
            event.site_id,
            {
                "site": event.site,
                "events": 0, "registered": 0, "members": 0, "guests": 0, "away": away.get(event.site_id, 0),
            },
        )
        row["events"] += 1
        row["registered"] += event.registered
        row["members"] += event.attended
        row["guests"] += event.guest_count
    rows = []
    for row in summary.values():
        row["total"] = row["members"] + row["guests"]
        row["average"] = round(row["total"] / row["events"], 1) if row["events"] else 0
        rows.append(row)
    rows.sort(key=lambda r: (not (r["site"] and r["site"].is_main), r["site"].name if r["site"] else ""))
    return rows


class AttendanceReportView(ManageMembersRequiredMixin, View):
    """Attendance totals per event, per site and per member over a date range."""

    template_name = "events/attendance_report.html"

    def get(self, request):
        data = attendance_report_data(request)
        tenant = request.user.tenant
        total_events = data["total_events"]
        page = Paginator(data["member_rows"], 50).get_page(request.GET.get("page"))
        for row in page:
            row.percent = round(row.attended * 100 / total_events) if total_events else 0

        # The filters as a query string (without the page), so every link --
        # export, pagination -- carries all of them, `site` included.
        query = request.GET.copy()
        query.pop("page", None)
        members_present = sum(r.attended for r in data["event_rows"])
        guests = sum(r.guest_count for r in data["event_rows"])

        return render(
            request,
            self.template_name,
            {
                "start": data["start"],
                "end": data["end"],
                "event_type": data["event_type"],
                "site_id": data["site_id"],
                "type_choices": Event.TYPE_CHOICES,
                "site_choices": Site.objects.filter(tenant=tenant) if tenant.uses_sites else None,
                "show_sites": tenant.uses_sites,
                "event_rows": data["event_rows"],
                "site_summary": data["site_summary"],
                "total_events": total_events,
                "total_attendances": members_present,
                "total_guests": guests,
                "total_people": members_present + guests,
                "querystring": query.urlencode(),
                "page": page,
            },
        )


attendance_report = AttendanceReportView.as_view()


class AttendanceExportView(ManageMembersRequiredMixin, View):
    """CSV of the attendance report: `?kind=events` (default, one row per event),
    `?kind=members` (one row per member who attended) or `?group=site` (one row
    per site)."""

    def get(self, request):
        data = attendance_report_data(request)
        total_events = data["total_events"]
        if request.GET.get("group") == "site":
            header = [
                "Sede", "Eventos", "Inscritos", "Asistieron (miembros)", "Visitas", "Total de personas",
                "Promedio por evento", "Miembros de otra sede",
            ]
            rows = (
                [
                    r["site"].name if r["site"] else "", r["events"], r["registered"], r["members"],
                    r["guests"], r["total"], r["average"], r["away"],
                ]
                for r in data["site_summary"]
            )
            name = "asistencia-por-sede"
        elif request.GET.get("kind") == "members":
            header = ["Nombre", "Apellido", "Email", "Asistencias", "% de eventos", "Última asistencia"]
            rows = (
                [
                    m.first_name, m.last_name, m.email, m.attended,
                    round(m.attended * 100 / total_events) if total_events else 0,
                    m.last_attended,
                ]
                for m in data["member_rows"]
            )
            name = "asistencia-por-miembro"
        else:
            header = ["Fecha", "Evento", "Tipo", "Inscritos", "Asistieron", "Visitas", "Sede"]
            rows = (
                [
                    e.start_at, e.title, e.get_event_type_display(), e.registered, e.attended,
                    e.guest_count, e.site.name if e.site else "",
                ]
                for e in data["event_rows"]
            )
            name = "asistencia-por-evento"
        return csv_response(export_filename(name), header, rows)


attendance_export = AttendanceExportView.as_view()
