"""
Automatic reminders: one e-mail 1 day and one 1 hour before each event starts,
to the people registered. The beat task calls `send_due_reminders` every few
minutes; `EventNotification` makes it safe to run as often (or late) as needed.
"""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import DateTimeField, ExpressionWrapper, F
from django.utils import timezone

from emails import notify

from .models import Event, EventNotification, EventRegistration

# kind: (how long before the start, how late it may still go out after that point)
WINDOWS = {
    "day_before": (timedelta(hours=24), timedelta(hours=6)),
    "hour_before": (timedelta(hours=1), timedelta(minutes=30)),
}
BATCH = 500


def send_due_reminders(now=None, batch=BATCH):
    """Queue every reminder that is due. Returns how many e-mails were queued.

    A reminder is due when the event starts within `lead` of now (and not more
    than `grace` earlier than that, so a worker that was down still catches up
    without sending stale ones). Events created, and people registered, after
    that moment get no reminder for it: they were told when they signed up."""
    now = now or timezone.now()
    queued = 0
    for kind, (lead, grace) in WINDOWS.items():
        events = (
            Event.objects.filter(
                is_active=True,
                reminders_enabled=True,
                start_at__lte=now + lead,
                start_at__gt=now + lead - grace,
                created_at__lte=ExpressionWrapper(F("start_at") - lead, output_field=DateTimeField()),
            )
            .select_related("tenant", "site")
            .order_by("start_at")
        )
        for event in events:
            if queued >= batch:
                return queued
            queued += _remind(event, kind, lead, batch - queued)
    return queued


def _remind(event, kind, lead, room):
    already = set(
        EventNotification.objects.filter(event=event, kind=kind).values_list("member_id", flat=True)
    )
    registrations = (
        EventRegistration.objects.filter(
            event=event, status="registered", registered_at__lte=event.start_at - lead
        )
        .exclude(member_id__in=already)
        .select_related("member")
    )
    queued = 0
    for registration in registrations:
        if queued >= room:
            break
        member = registration.member
        try:
            with transaction.atomic():
                EventNotification.objects.create(
                    tenant_id=event.tenant_id, event=event, member=member, kind=kind
                )
        except IntegrityError:  # another worker got there first
            continue
        if notify.event_reminder(event, member, kind):
            queued += 1
        else:
            EventNotification.objects.filter(event=event, member=member, kind=kind).update(
                status="skipped"
            )
    return queued
