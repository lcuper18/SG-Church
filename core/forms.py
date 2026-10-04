"""Forms for the profile and church-settings pages."""

from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from members.models import User
from tenants.models import Tenant
from tenants.timezones import TIMEZONE_CHOICES


class BootstrapFormMixin:
    """Gives every widget its Bootstrap class and flags fields with errors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            widget = self.fields[name].widget if name in self.fields else None
            if widget is not None:
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid"


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    # The email is the login identifier (django-allauth keeps its own record of
    # it), so it is shown but not editable here.
    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        labels = {"first_name": "Nombre", "last_name": "Apellido"}


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class ChurchSettingsForm(BootstrapFormMixin, forms.ModelForm):
    timezone = forms.ChoiceField(label="Zona horaria", choices=TIMEZONE_CHOICES)

    class Meta:
        model = Tenant
        fields = [
            "name",
            "denomination",
            "country",
            "city",
            "state",
            "address",
            "phone",
            "email",
            "currency",
            "timezone",
            "enable_families",
            "enable_tags",
        ]
        labels = {
            "name": "Nombre de la iglesia",
            "denomination": "Denominación",
            "country": "País",
            "city": "Ciudad",
            "state": "Estado / provincia",
            "address": "Dirección",
            "phone": "Teléfono",
            "email": "Email de contacto",
            "currency": "Moneda",
            "enable_families": "Usar familias",
            "enable_tags": "Usar etiquetas",
        }
        help_texts = {"country": ""}
        widgets = {"address": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tenants created before the zone list was extended may hold a zone
        # that is not offered any more; keep it selectable instead of
        # silently switching it on save.
        current = self.instance.timezone
        if current and current not in dict(TIMEZONE_CHOICES):
            self.fields["timezone"].choices = [(current, current), *TIMEZONE_CHOICES]
