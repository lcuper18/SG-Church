"""
Event and registration views.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import ManageMembersRequiredMixin
from education.models import Course
from members.models import Member

from .models import Event, EventRegistration

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
