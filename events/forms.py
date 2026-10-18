"""Forms for creating and editing events, including "Repetir"."""

from django import forms
from django.utils import timezone

from members.models import Tag

from . import announcements, recurrence
from .models import Event, EventAnnouncement

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
    "reminders_enabled",
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


class AnnouncementForm(forms.Form):
    """A custom announcement for an event: what to say, to whom, and when."""

    subject = forms.CharField(max_length=150, label="Asunto")
    body = forms.CharField(widget=forms.Textarea, max_length=5000, label="Mensaje")
    audience = forms.ChoiceField(choices=EventAnnouncement.AUDIENCE_CHOICES, label="Destinatarios")
    tag = forms.ModelChoiceField(queryset=Tag.objects.none(), required=False, label="Etiqueta")
    when = forms.ChoiceField(choices=[("now", "Enviar ahora"), ("later", "Programar")], initial="now")
    send_at = forms.DateTimeField(required=False, label="Enviar el")

    def __init__(self, *args, event, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["tag"].queryset = Tag.objects.filter(tenant=event.tenant)
        self.recipients = 0

    def clean(self):
        cleaned = super().clean()
        event = self.event
        if not event.is_active or event.is_past:
            raise forms.ValidationError("Solo se pueden enviar anuncios de eventos activos que aún no terminan.")
        audience, tag = cleaned.get("audience"), cleaned.get("tag")
        if audience == "tag" and not tag:
            self.add_error("tag", "Elige la etiqueta.")
        if cleaned.get("when") == "later":
            send_at = cleaned.get("send_at")
            if not send_at:
                self.add_error("send_at", "Indica cuándo enviarlo.")
            elif send_at <= timezone.now():
                self.add_error("send_at", "La fecha de envío debe ser en el futuro.")
            elif send_at >= (event.end_at or event.start_at):
                self.add_error("send_at", "Debe ser antes de que termine el evento.")
        if audience and not self.errors:
            self.recipients = announcements.audience_members(
                event.tenant, event, audience, tag if audience == "tag" else None
            ).count()
            if self.recipients == 0:
                raise forms.ValidationError("No hay a quién enviarlo: nadie con correo en ese grupo.")
            if self.recipients > EventAnnouncement.MAX_RECIPIENTS:
                raise forms.ValidationError(
                    f"Son {self.recipients} destinatarios; el máximo por anuncio es {EventAnnouncement.MAX_RECIPIENTS}."
                )
        return cleaned
