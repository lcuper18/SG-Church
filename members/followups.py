"""
Pastoral follow-up: who needs a call or a visit, who is in charge, what was said.
Only admins and pastors (see `User.can_view_pastoral_notes`).
"""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from core.mixins import PastoralRequiredMixin
from events.models import EventAttendance

from .forms import FollowUpForm
from .models import FollowUp, Member

# A regular who has not been to anything for this long is worth a call.
AWAY_DAYS = 42
LOOKBACK_DAYS = 120
NEW_VISITOR_DAYS = 30
SUGGESTION_LIMIT = 30


def suggestions(tenant, today=None):
    """(new visitors nobody has contacted, regulars who stopped coming). Suggestions
    are computed, never stored, and skip anyone with a recent follow-up."""
    now = timezone.now()
    recent_contact = Member.objects.filter(
        tenant=tenant, follow_ups__created_at__gte=now - timedelta(days=AWAY_DAYS)
    ).values("pk")

    visitors = (
        Member.objects.filter(
            tenant=tenant,
            member_status="visitor",
            created_at__gte=now - timedelta(days=NEW_VISITOR_DAYS),
        )
        .annotate(contacts=Count("follow_ups"))
        .filter(contacts=0)
        .order_by("-created_at")[:SUGGESTION_LIMIT]
    )

    cutoff = now - timedelta(days=AWAY_DAYS)
    recent_events_held = EventAttendance.objects.filter(
        tenant=tenant, event__start_at__gte=cutoff
    ).exists()
    away = Member.objects.none()
    if recent_events_held:  # no attendance taken lately: nobody can be called "absent"
        before = EventAttendance.objects.filter(
            tenant=tenant,
            event__start_at__gte=now - timedelta(days=LOOKBACK_DAYS),
            event__start_at__lt=cutoff,
        ).values("member_id")
        since = EventAttendance.objects.filter(
            tenant=tenant, event__start_at__gte=cutoff
        ).values("member_id")
        away = (
            Member.objects.filter(tenant=tenant, member_status__in=["member", "attendee"], pk__in=before)
            .exclude(pk__in=since)
            .exclude(pk__in=recent_contact)
            .order_by("last_name", "first_name")[:SUGGESTION_LIMIT]
        )
    return list(visitors), list(away)


class FollowUpListView(LoginRequiredMixin, PastoralRequiredMixin, View):
    template_name = "members/followups.html"

    def get(self, request):
        tenant = request.user.tenant
        status = request.GET.get("status", "open")
        who = request.GET.get("who", "mine")
        items = FollowUp.objects.filter(tenant=tenant).select_related("member", "assigned_to")
        if status in ("open", "done"):
            items = items.filter(status=status)
        if who == "mine":
            items = items.filter(assigned_to=request.user)
        elif who == "unassigned":
            items = items.filter(assigned_to__isnull=True)
        today = timezone.localdate()
        items = list(items.order_by("due_date", "-created_at")[:200]) if status != "done" else list(
            items.order_by("-completed_at")[:200]
        )
        for item in items:
            item.overdue = item.status == "open" and item.due_date is not None and item.due_date < today
        counts = FollowUp.objects.filter(tenant=tenant, status="open").aggregate(
            mine=Count("pk", filter=Q(assigned_to=request.user)),
            overdue=Count("pk", filter=Q(due_date__lt=today)),
            total=Count("pk"),
        )
        visitors, away = suggestions(tenant)
        return render(
            request,
            self.template_name,
            {
                "items": items,
                "status": status,
                "who": who,
                "counts": counts,
                "visitors": visitors,
                "away": away,
                "today": today,
            },
        )


follow_up_list = FollowUpListView.as_view()


def _back(request, member):
    if request.POST.get("back") == "list":
        return redirect("follow_up_list")
    return redirect(reverse("member_detail", args=[member.pk]) + "#followups")


class FollowUpAddView(LoginRequiredMixin, PastoralRequiredMixin, View):
    """Record a follow-up for a member (POST only). From the member's page it is
    the full form; from the suggestions it is a one-click "call them today"."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk, tenant=request.user.tenant)
        form = FollowUpForm(request.POST, tenant=request.user.tenant)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return _back(request, member)
        item = form.save(commit=False)
        item.tenant, item.member, item.created_by = request.user.tenant, member, request.user
        if item.assigned_to is None and not form.cleaned_data["done"]:
            item.assigned_to = request.user
        if form.cleaned_data["done"]:
            item.status, item.completed_at = "done", timezone.now()
        item.save()
        messages.success(request, "Seguimiento registrado.")
        return _back(request, member)


follow_up_add = FollowUpAddView.as_view()


class FollowUpObjectMixin(LoginRequiredMixin, PastoralRequiredMixin):
    def item(self, request, pk):
        return get_object_or_404(FollowUp, pk=pk, tenant=request.user.tenant)


class FollowUpEditView(FollowUpObjectMixin, View):
    template_name = "members/followup_form.html"

    def get(self, request, pk):
        item = self.item(request, pk)
        form = FollowUpForm(instance=item, tenant=request.user.tenant)
        return render(request, self.template_name, {"form": form, "item": item})

    def post(self, request, pk):
        item = self.item(request, pk)
        form = FollowUpForm(request.POST, instance=item, tenant=request.user.tenant)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "item": item})
        saved = form.save(commit=False)
        if form.cleaned_data["done"] and saved.status != "done":
            saved.status, saved.completed_at = "done", timezone.now()
        elif not form.cleaned_data["done"] and saved.status == "done":
            saved.status, saved.completed_at = "open", None
        saved.save()
        messages.success(request, "Seguimiento actualizado.")
        return redirect(reverse("member_detail", args=[item.member_id]) + "#followups")


follow_up_edit = FollowUpEditView.as_view()


class FollowUpDoneView(FollowUpObjectMixin, View):
    """Mark as done and, if a date is given, plan the next contact right away (POST only)."""

    def post(self, request, pk):
        item = self.item(request, pk)
        if item.status == "open":
            item.mark_done()
        next_due = request.POST.get("next_due")
        if next_due:
            try:
                due = date.fromisoformat(next_due)
            except ValueError:
                due = None
            if due:
                FollowUp.objects.create(
                    tenant=item.tenant, member=item.member, kind=item.kind, due_date=due,
                    assigned_to=item.assigned_to or request.user, created_by=request.user,
                )
                messages.success(request, "Hecho. Quedó programado el siguiente contacto.")
                return _back(request, item.member)
        messages.success(request, "Marcado como hecho.")
        return _back(request, item.member)


follow_up_done = FollowUpDoneView.as_view()


class FollowUpReopenView(FollowUpObjectMixin, View):
    def post(self, request, pk):
        item = self.item(request, pk)
        if item.status == "done":
            item.reopen()
        return _back(request, item.member)


follow_up_reopen = FollowUpReopenView.as_view()


class FollowUpDeleteView(FollowUpObjectMixin, View):
    def post(self, request, pk):
        item = self.item(request, pk)
        member = item.member
        item.delete()
        messages.success(request, "Seguimiento eliminado.")
        return _back(request, member)


follow_up_delete = FollowUpDeleteView.as_view()
