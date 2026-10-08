"""Forms for the profile and church-settings pages."""

import secrets

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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


ROLE_HELP = {
    "admin": "Acceso total: miembros, finanzas, cursos, configuración y usuarios.",
    "pastor": "Gestiona miembros, familias, etiquetas y eventos.",
    "treasurer": "Gestiona donaciones, gastos y reportes de finanzas.",
    "teacher": "Gestiona cursos, bloques y certificados.",
    "volunteer": "Gestiona miembros y eventos (inscripciones y asistencia).",
    "member": "Solo consulta; no puede crear ni modificar datos.",
}


class _PasswordPairMixin:
    """`password1`/`password2` fields validated with the project's validators."""

    def _add_password_fields(self, required):
        self.fields["password1"] = forms.CharField(
            label="Contraseña" if required else "Nueva contraseña",
            required=required,
            strip=False,
            widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
            help_text=(
                "Mínimo 8 caracteres; no puede ser común ni solo números."
                if required
                else "Déjala en blanco para no cambiarla."
            ),
        )
        self.fields["password2"] = forms.CharField(
            label="Repite la contraseña",
            required=required,
            strip=False,
            widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        )

    def _clean_passwords(self, cleaned, user):
        password1, password2 = cleaned.get("password1"), cleaned.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif password1:
                try:
                    validate_password(password1, user)
                except ValidationError as error:
                    self.add_error("password1", error)


class UserCreateForm(_PasswordPairMixin, BootstrapFormMixin, forms.ModelForm):
    """Create a login for a person in the administrator's own church."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Email (para iniciar sesión)",
            "role": "Rol",
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.fields["email"].required = True
        self.fields["first_name"].required = True
        self._add_password_fields(required=True)

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"]).strip()
        # Email is the global login identifier, so it must be unique across
        # every church, not just this one.
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe un usuario con ese email.")
        return email

    def clean(self):
        cleaned = super().clean()
        self._clean_passwords(cleaned, User(email=cleaned.get("email", "")))
        return cleaned

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        username = email.split("@")[0]
        if User.objects.filter(username=username).exists():
            username = f"{username}-{secrets.token_hex(2)}"
        return User.objects.create_user(
            email=email,
            password=self.cleaned_data["password1"],
            username=username,
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            role=self.cleaned_data["role"],
            tenant=self.tenant,
        )


class UserEditForm(_PasswordPairMixin, BootstrapFormMixin, forms.ModelForm):
    """Change a user's name, role, active state and (optionally) password.

    Administrators can't change their own role or deactivate themselves, so a
    church can never lock itself out; those fields are disabled for them."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "is_active"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "role": "Rol",
            "is_active": "Puede iniciar sesión",
        }

    def __init__(self, *args, editing_self=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing_self = editing_self
        if editing_self:
            for name in ("role", "is_active"):
                self.fields[name].disabled = True
            self.fields["role"].help_text = "No puedes cambiar tu propio rol."
        else:
            # Own password changes go through "Mi perfil", which keeps the
            # session alive; here it would log the administrator out.
            self._add_password_fields(required=False)

    def clean(self):
        cleaned = super().clean()
        self._clean_passwords(cleaned, self.instance)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
