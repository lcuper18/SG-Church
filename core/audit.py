"""
Audit trail ("bitácora"): who created, changed, deleted or restored what.

Entries are written by `post_save` handlers on the registered models, so every
path is covered -- web views, the API, the admin, scripts -- without each view
having to remember. The acting user comes from the current request (stored by
`AuditContextMiddleware`); outside a request (seed, Celery, webhooks) the actor
is "Sistema". A failure to write an entry never breaks the action itself.
"""

import contextlib
import contextvars
import logging
from datetime import date, datetime
from decimal import Decimal

from django.db.models.signals import post_save, pre_save

logger = logging.getLogger(__name__)

_current_request = contextvars.ContextVar("audit_request", default=None)
_suppressed = contextvars.ContextVar("audit_suppressed", default=False)

# Never stored, not even as a value change.
ALWAYS_SKIP = {
    "id", "created_at", "updated_at", "last_login", "search_text", "deleted_at", "deleted_by",
    "national_id_key",
}
# Recorded as "changed" without showing the content.
MASKED = {"password", "notes", "photo", "national_id"}

REGISTRY = {}  # model -> Spanish name


def current_user():
    request = _current_request.get()
    user = getattr(request, "user", None)
    return user if getattr(user, "is_authenticated", False) else None


@contextlib.contextmanager
def suppressed():
    """Skip the per-record entries inside the block (a bulk job writes one
    summary line with `log_note` instead)."""
    token = _suppressed.set(True)
    try:
        yield
    finally:
        _suppressed.reset(token)


def set_request(request):
    return _current_request.set(request)


def reset_request(token):
    _current_request.reset(token)


def _tracked_fields(model):
    return [f for f in model._meta.concrete_fields if f.name not in ALWAYS_SKIP]


def _plain(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _snapshot(instance):
    return {f.attname: _plain(getattr(instance, f.attname)) for f in _tracked_fields(type(instance))}


def _tenant_id(instance):
    from tenants.models import Tenant

    if isinstance(instance, Tenant):
        return instance.pk
    return getattr(instance, "tenant_id", None)


def _write(instance, action, user, changes=None):
    from core.models import AuditLog

    tenant_id = _tenant_id(instance)
    if tenant_id is None:
        return
    try:
        AuditLog.objects.create(
            tenant_id=tenant_id,
            user=user,
            user_label=(user.email or user.get_full_name()) if user else "Sistema",
            action=action,
            model_label=instance._meta.label_lower,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            changes=changes or {},
        )
    except Exception:  # noqa: BLE001 - auditing must never break the action
        logger.exception("Could not write the audit entry")


def log_note(tenant, user, action, model_label, text):
    """One free-text entry, e.g. "Importación CSV: 40 nuevos"."""
    from core.models import AuditLog

    try:
        AuditLog.objects.create(
            tenant=tenant,
            user=user,
            user_label=(user.email or user.get_full_name()) if user else "Sistema",
            action=action,
            model_label=model_label,
            object_id="",
            object_repr=text[:255],
        )
    except Exception:  # noqa: BLE001
        logger.exception("Could not write the audit entry")


def log_action(instance, action, user=None):
    """Record delete/restore/purge (create/update come from signals)."""
    if type(instance) in REGISTRY:
        _write(instance, action, user if user is not None else current_user())


def _before_save(sender, instance, **kwargs):
    instance._audit_before = None
    if _suppressed.get():
        return
    if instance._state.adding or instance.pk is None:
        return
    try:
        old = sender._base_manager.filter(pk=instance.pk).first()
        instance._audit_before = _snapshot(old) if old else None
    except Exception:  # noqa: BLE001
        logger.exception("Could not read the previous state for the audit trail")


def _after_save(sender, instance, created, **kwargs):
    if _suppressed.get():
        return
    if created:
        _write(instance, "create", current_user())
        return
    before = getattr(instance, "_audit_before", None)
    if before is None:
        return
    after = _snapshot(instance)
    changes = {}
    # attname ("family_id") -> field name ("family"); stripping "_id" by hand would
    # also mangle fields like national_id and defeat the masking below.
    names = {f.attname: f.name for f in _tracked_fields(type(instance))}
    for name, old in before.items():
        new = after.get(name)
        if old != new:
            field = names.get(name, name)
            changes[field] = ["•••", "•••"] if field in MASKED else [old, new]
    if changes:
        _write(instance, "update", current_user(), changes)


def register(model, label):
    """Start auditing `model`; `label` is its name in the UI ("Miembro")."""
    REGISTRY[model] = label
    pre_save.connect(_before_save, sender=model, dispatch_uid=f"audit-pre-{model._meta.label}")
    post_save.connect(_after_save, sender=model, dispatch_uid=f"audit-post-{model._meta.label}")


def label_for(model_label):
    from django.apps import apps

    try:
        return REGISTRY.get(apps.get_model(model_label), model_label)
    except LookupError:
        return model_label


class AuditContextMiddleware:
    """Remember the request so signal handlers can tell who is acting."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_request(request)
        try:
            return self.get_response(request)
        finally:
            reset_request(token)


# Spanish names for the fields shown in the audit page; anything missing is
# shown with its underscores replaced.
FIELD_LABELS = {
    "first_name": "Nombre", "last_name": "Apellido", "email": "Correo", "phone": "Teléfono",
    "date_of_birth": "Fecha de nacimiento", "gender": "Género", "marital_status": "Estado civil",
    "site": "Sede", "series": "Serie", "original_start_at": "Horario original", "weekdays": "Días", "start_time": "Hora de inicio", "end_time": "Hora de fin", "first_date": "Primera fecha", "until_date": "Última fecha", "home_site": "Sede de origen", "is_main": "Sede principal", "sort_order": "Orden", "national_id": "Identificación", "is_baptized": "Bautizado", "baptism_date": "Fecha de bautismo", "member_status": "Estado",
    "membership_date": "Fecha de membresía", "family": "Familia", "address": "Dirección",
    "city": "Ciudad", "state": "Estado/provincia", "postal_code": "Código postal",
    "notes": "Notas", "photo": "Foto", "user": "Usuario", "name": "Nombre", "color": "Color",
    "head_of_family": "Cabeza de familia", "home_phone": "Teléfono de casa",
    "email_opt_out": "No recibir correos de avisos", "subject": "Asunto", "body": "Mensaje", "audience": "Destinatarios", "send_at": "Envío programado", "tag": "Etiqueta", "role": "Rol", "is_active": "Activo", "reminders_enabled": "Recordatorios automáticos", "member_profile": "Ficha de miembro",
    "password": "Contraseña", "title": "Título", "description": "Descripción",
    "event_type": "Tipo", "location": "Lugar", "start_at": "Inicio", "end_at": "Fin",
    "capacity": "Cupo", "requires_baptized": "Requiere bautizo", "requires_married": "Requiere casado/a",
    "instructor": "Instructor", "course_block": "Bloque", "order_in_block": "Orden en el bloque",
    "amount": "Monto", "currency": "Moneda", "status": "Estado", "campaign": "Campaña",
    "donation_type": "Tipo", "donor_name": "Donante", "donor_email": "Correo del donante",
    "anonymous": "Anónima", "payment_method": "Método de pago", "category": "Categoría",
    "vendor_name": "Proveedor", "expense_date": "Fecha del gasto", "due_date": "Vencimiento",
    "approved_by": "Aprobado por", "created_by": "Creado por", "receipt": "Recibo",
    "timezone": "Zona horaria", "country": "País", "denomination": "Denominación",
    "enable_families": "Usar familias", "enable_tags": "Usar etiquetas",
    "certificate_signer_name": "Firma de certificados", "certificate_signer_title": "Cargo de la firma",
    "completed_at": "Completado", "course": "Curso", "member": "Miembro",
}


def field_label(name):
    return FIELD_LABELS.get(name, name.replace("_", " ").capitalize())
