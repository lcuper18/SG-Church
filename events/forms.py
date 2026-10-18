"""Forms for creating and editing events, including "Repetir"."""

from django import forms
from django.utils import timezone

from . import recurrence
from .models import Event

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
    "site",
]

WEEKDAY_CHOICES = [
    (0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"), (4, "Viernes"),
    (5, "Sábado"), (6, "Domingo"),
]


class EventForm(forms.ModelForm):
    """The event itself. When creating, it can also describe a repetition; when
    editing an occurrence of a series, which occurrences the change applies to."""

    repeat = forms.BooleanField(required=False, label="Repetir")
    repeat_weekdays = forms.MultipleChoiceField(
        required=False, choices=WEEKDAY_CHOICES, label="Días de la semana"
    )
    repeat_end = forms.ChoiceField(
        required=False, choices=[("until", "Hasta una fecha"), ("weeks", "Durante unas semanas")], initial="weeks"
    )
    repeat_until = forms.DateField(required=False, label="Hasta")
    repeat_weeks = forms.IntegerField(required=False, min_value=1, max_value=52, label="Semanas")
    edit_scope = forms.ChoiceField(
        required=False, choices=[("this", "Solo este evento"), ("following", "Este y los siguientes")], initial="this"
    )

    class Meta:
        model = Event
        fields = EVENT_FIELDS

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.is_new = self.instance._state.adding  # pk is a UUID assigned on creation
        self.rule = None  # filled by clean() when repeating

    def clean(self):
        cleaned = super().clean()
        if self.is_new and cleaned.get("repeat"):
            start_at, end_at = cleaned.get("start_at"), cleaned.get("end_at")
            if start_at is None:
                return cleaned  # the field error is already reported
            if start_at <= timezone.now():
                self.add_error("start_at", "Para repetir, el primer evento debe ser en el futuro.")
                return cleaned
            if end_at and end_at <= start_at:
                self.add_error("end_at", "El fin debe ser posterior al inicio.")
                return cleaned
            until = cleaned.get("repeat_until") if cleaned.get("repeat_end") == "until" else None
            weeks = cleaned.get("repeat_weeks") if cleaned.get("repeat_end") != "until" else None
            try:
                tz = recurrence.zone_for(self.tenant)
                first = timezone.localtime(start_at, tz).date()
                weekdays = {int(d) for d in cleaned.get("repeat_weekdays") or []} | {first.weekday()}
                dates, _ = recurrence.occurrence_dates(first, weekdays, until, weeks)
            except recurrence.RecurrenceError as error:
                self.add_error(None, str(error))
                return cleaned
            self.rule = {"weekdays": weekdays, "until_date": until, "weeks": weeks, "count": len(dates)}
        return cleaned
