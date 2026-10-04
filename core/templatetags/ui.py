from django import template

register = template.Library()

MEMBER_STATUS_COLORS = {
    "member": "success",
    "visitor": "warning",
    "attendee": "info",
}


@register.simple_tag(takes_context=True)
def page_url(context, page):
    """URL de la página `page` conservando los filtros actuales del querystring."""
    params = context["request"].GET.copy()
    params["page"] = page
    return "?" + params.urlencode()


@register.filter
def member_status_color(status):
    return MEMBER_STATUS_COLORS.get(status, "secondary")


@register.filter
def invalid(field):
    """Clase de Bootstrap para marcar un campo con errores de validación."""
    return "is-invalid" if getattr(field, "errors", None) else ""


TRANSACTION_STATUS = {
    "completed": ("Completado", "success"),
    "paid": ("Pagado", "success"),
    "approved": ("Aprobado", "info"),
    "pending": ("Pendiente", "warning"),
    "failed": ("Fallido", "danger"),
    "rejected": ("Rechazado", "danger"),
    "refunded": ("Reembolsado", "secondary"),
}


@register.filter
def transaction_status_label(status):
    return TRANSACTION_STATUS.get(status, (status, ""))[0]


@register.filter
def transaction_status_color(status):
    return TRANSACTION_STATUS.get(status, ("", "secondary"))[1] or "secondary"
