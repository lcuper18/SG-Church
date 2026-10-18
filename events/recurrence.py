"""
Repeating events ("Repetir"): weekly cultos and meetings.

A series is a rule (`EventSeries`) plus one ordinary `Event` per date. Every
occurrence stays editable, cancellable and deletable on its own. Times are kept
as the church's wall-clock time: a Wednesday 7 pm culto stays at 7 pm after the
clocks change, and the stored (UTC) instants move accordingly.
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone as dj_timezone

from tenants.timezones import get_zone

from .models import Event, EventAttendance, EventSeries

MAX_OCCURRENCES = 52
MAX_SPAN_DAYS = 366
UTC = dt_timezone.utc

# Fields copied to every occurrence (and propagated by "this and the following").
CONTENT_FIELDS = (
    "title", "description", "event_type", "location", "capacity", "requires_baptized",
    "requires_married", "is_active", "reminders_enabled", "site",
)


class RecurrenceError(ValueError):
    """The repetition asked for is not valid; the message is shown to the user."""


def zone_for(tenant):
    from zoneinfo import ZoneInfo

    return get_zone(tenant.timezone) or ZoneInfo("UTC")


def localize(day, clock, tz):
    """The UTC instant of `day` at wall-clock `clock` in `tz`. A time that does not
    exist (spring-forward gap) moves to the first valid one; an ambiguous time
    (clocks fall back) takes its first occurrence."""
    naive = datetime.combine(day, clock)
    aware = naive.replace(tzinfo=tz)
    back = aware.astimezone(UTC).astimezone(tz)
    if back.replace(tzinfo=None) != naive:
        aware = back
    return aware.astimezone(UTC)


def window(day, start_time, end_time, tz):
    """(start, end) in UTC for one occurrence; `end` is None without an end time and
    rolls to the next day when it is not after the start (a culto ending past midnight)."""
    start = localize(day, start_time, tz)
    if end_time is None:
        return start, None
    end = localize(day, end_time, tz)
    if end <= start:
        end = localize(day + timedelta(days=1), end_time, tz)
    return start, end


def occurrence_dates(first_date, weekdays, until_date=None, weeks=None):
    """The dates of the series, validated: at least one weekday, an end (date or
    number of weeks), a sane span and no more than MAX_OCCURRENCES."""
    weekdays = sorted({int(d) for d in weekdays})
    if not weekdays:
        raise RecurrenceError("Elige al menos un día de la semana para repetir.")
    if any(d < 0 or d > 6 for d in weekdays):
        raise RecurrenceError("Días de la semana no válidos.")
    if weeks:
        if weeks < 1:
            raise RecurrenceError("Las semanas deben ser al menos 1.")
        until_date = first_date + timedelta(days=7 * weeks - 1)
    if until_date is None:
        raise RecurrenceError("Indica hasta cuándo se repite (una fecha o un número de semanas).")
    if until_date < first_date:
        raise RecurrenceError("La fecha final no puede ser anterior al primer evento.")
    if (until_date - first_date).days + 1 > MAX_SPAN_DAYS:
        raise RecurrenceError("La repetición no puede durar más de un año.")
    dates, day = [], first_date
    while day <= until_date:
        if day.weekday() in weekdays:
            dates.append(day)
        day += timedelta(days=1)
    if not dates:
        raise RecurrenceError("Con esos días no se genera ningún evento en el período indicado.")
    if len(dates) > MAX_OCCURRENCES:
        raise RecurrenceError(
            f"Eso generaría {len(dates)} eventos y el máximo es {MAX_OCCURRENCES}. "
            "Acorta el período o crea otra serie después."
        )
    return dates, until_date


@transaction.atomic
def create_series(*, tenant, user, fields, courses, site, start_at, end_at, weekdays, until_date=None, weeks=None):
    """Create the series and its occurrences from the first event's data. Returns
    (series, [events]). `fields` are the plain Event fields (CONTENT_FIELDS minus
    `site`); `start_at`/`end_at` are the first occurrence, as aware datetimes."""
    tz = zone_for(tenant)
    first_local = dj_timezone.localtime(start_at, tz)
    first_date, start_time = first_local.date(), first_local.time()
    end_time = dj_timezone.localtime(end_at, tz).time() if end_at else None
    weekdays = {int(d) for d in weekdays} | {first_date.weekday()}
    dates, until = occurrence_dates(first_date, weekdays, until_date, weeks)

    series = EventSeries.objects.create(
        tenant=tenant, site=site, weekdays=sorted(weekdays), start_time=start_time, end_time=end_time,
        first_date=first_date, until_date=until, timezone=str(tz), created_by=user,
    )
    events = []
    for day in dates:
        start, end = window(day, start_time, end_time, tz)
        event = Event(
            tenant=tenant, site=site, series=series, original_start_at=start,
            start_at=start, end_at=end, **fields,
        )
        event.save()
        event.required_courses.set(courses)
        events.append(event)
    return series, events


def _without_attendance(queryset):
    return queryset.annotate(
        _held=Exists(EventAttendance.objects.filter(event=OuterRef("pk")))
    ).filter(_held=False)


def following(pivot, *, include_pivot=True):
    """Occurrences of the pivot's series from the pivot on that can still be
    changed: alive, in the future and with no attendance taken."""
    if not pivot.series_id:
        return Event.objects.filter(pk=pivot.pk)
    scope = Event.objects.filter(
        series_id=pivot.series_id, original_start_at__gte=pivot.original_start_at, start_at__gt=dj_timezone.now()
    )
    scope = _without_attendance(scope)
    if not include_pivot:
        scope = scope.exclude(pk=pivot.pk)
    return scope.order_by("original_start_at")


def _split_series(pivot, scope_ids):
    """Move the scope to a new series so the earlier occurrences keep the old
    rule. If the pivot is the series' first occurrence nothing needs splitting."""
    series = pivot.series
    earlier = Event.objects.filter(series=series, original_start_at__lt=pivot.original_start_at).exists()
    if not earlier:
        return series
    tz = zone_for(pivot.tenant)
    pivot_day = dj_timezone.localtime(pivot.original_start_at, tz).date()
    new = EventSeries.objects.create(
        tenant=series.tenant, site=pivot.site, weekdays=series.weekdays, start_time=series.start_time,
        end_time=series.end_time, first_date=pivot_day, until_date=series.until_date,
        timezone=series.timezone, created_by=series.created_by,
    )
    series.until_date = pivot_day - timedelta(days=1)
    series.save(update_fields=["until_date"])
    Event.objects.filter(pk__in=scope_ids).update(series=new)
    return new


@transaction.atomic
def update_following(pivot, changed, courses=None):
    """Apply to every later occurrence the fields the user actually changed on the
    pivot (so an occurrence someone edited by hand keeps its own other values).
    A new time of day is applied to each occurrence's own date. Returns how many
    other occurrences were updated."""
    scope = list(following(pivot, include_pivot=True))
    pivot_in_scope = any(event.pk == pivot.pk for event in scope)
    series = _split_series(pivot, [e.pk for e in scope]) if pivot_in_scope else pivot.series
    pivot.series = series
    # Reload after the split: stale copies would write the old series back on save().
    others = list(following(pivot, include_pivot=False))

    time_changed = bool({"start_at", "end_at"} & set(changed))
    tz = zone_for(pivot.tenant)
    new_start = dj_timezone.localtime(pivot.start_at, tz).time()
    new_end = dj_timezone.localtime(pivot.end_at, tz).time() if pivot.end_at else None
    if time_changed and series and pivot_in_scope:
        series.start_time, series.end_time = new_start, new_end
        series.save(update_fields=["start_time", "end_time"])

    for event in others:
        for name in CONTENT_FIELDS:
            if name in changed:
                setattr(event, name, getattr(pivot, name))
        if time_changed:
            day = dj_timezone.localtime(event.start_at, tz).date()
            event.start_at, event.end_at = window(day, new_start, new_end, tz)
        event.save()
        if courses is not None and "required_courses" in changed:
            event.required_courses.set(courses)
    return len(others)


@transaction.atomic
def cancel(pivot, *, scope="this"):
    """Deactivate the pivot, or it and the later changeable occurrences. Returns
    the events that were active and are now cancelled."""
    targets = list(following(pivot) if scope == "following" else Event.objects.filter(pk=pivot.pk))
    cancelled = []
    for event in targets:
        if event.is_active:
            event.is_active = False
            event.save(update_fields=["is_active"])
            cancelled.append(event)
    return cancelled


@transaction.atomic
def delete(pivot, *, scope="this"):
    """Send the pivot, or it and the later changeable occurrences, to the trash."""
    targets = list(following(pivot) if scope == "following" else Event.objects.filter(pk=pivot.pk))
    for event in targets:
        event.delete()
    return len(targets)
