"""
Custom announcements: the event's manager writes a message and sends it to the
people registered, or to the members with a tag, now or at a chosen time.
The beat task (every 5 minutes) sends the ones that are due; the ledger
(`EventNotification`) makes a retry safe.
"""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from emails import notify
from members.models import Member

from .models import EventAnnouncement, EventNotification

STALE_AFTER = timedelta(minutes=15)  # a "sending" announcement older than this was interrupted
BATCH = 200


def audience_members(tenant, event, audience, tag=None):
    """Members (with an e-mail address, and who have not opted out) an announcement would reach."""
    if audience == "tag":
        members = Member.objects.filter(tenant=tenant, tags=tag) if tag else Member.objects.none()
    else:
        members = Member.objects.filter(
            tenant=tenant, event_registrations__event=event, event_registrations__status="registered"
        )
    return members.exclude(email="").exclude(email_opt_out=True).distinct()


def send_due(now=None):
    """Send the announcements that are due (and resume interrupted ones).
    Returns how many were processed."""
    now = now or timezone.now()
    processed = 0
    due = EventAnnouncement.objects.filter(
        Q(send_at__isnull=True) | Q(send_at__lte=now), status="scheduled"
    ).values_list("pk", flat=True)
    for pk in list(due):
        claimed = EventAnnouncement.objects.filter(pk=pk, status="scheduled").update(
            status="sending", updated_at=now
        )
        if claimed:
            deliver(EventAnnouncement.objects.get(pk=pk), now)
            processed += 1
    stale = EventAnnouncement.objects.filter(status="sending", updated_at__lt=now - STALE_AFTER)
    for pk in list(stale.values_list("pk", flat=True)):
        claimed = EventAnnouncement.objects.filter(
            pk=pk, status="sending", updated_at__lt=now - STALE_AFTER
        ).update(updated_at=now)
        if claimed:
            deliver(EventAnnouncement.objects.get(pk=pk), now)
            processed += 1
    return processed


def deliver(announcement, now):
    event = announcement.event
    if event.deleted_at or not event.is_active or (event.end_at or event.start_at) < now:
        announcement.status = "skipped"
        announcement.save(update_fields=["status", "updated_at"])
        return
    members = audience_members(announcement.tenant, event, announcement.audience, announcement.tag)
    done = set(announcement.notifications.values_list("member_id", flat=True))
    pending = [m for m in members[: EventAnnouncement.MAX_RECIPIENTS] if m.pk not in done]
    for start in range(0, len(pending), BATCH):
        for member in pending[start : start + BATCH]:
            try:
                with transaction.atomic():
                    EventNotification.objects.create(
                        tenant_id=announcement.tenant_id, event=event, member=member,
                        kind="announcement", announcement=announcement,
                    )
            except IntegrityError:
                continue
            if not notify.event_announcement(announcement, member):
                EventNotification.objects.filter(announcement=announcement, member=member).update(
                    status="skipped"
                )
    announcement.recipient_count = announcement.notifications.filter(status="queued").count()
    announcement.status = "sent"
    announcement.sent_at = timezone.now()
    announcement.save(update_fields=["recipient_count", "status", "sent_at", "updated_at"])


def cancel(announcement):
    """Cancel while it is still waiting. Returns True if it was cancelled."""
    return bool(
        EventAnnouncement.objects.filter(pk=announcement.pk, status="scheduled").update(
            status="cancelled", updated_at=timezone.now()
        )
    )
