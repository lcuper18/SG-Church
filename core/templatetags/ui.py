from decimal import Decimal, InvalidOperation

from django import template
from django.utils.formats import number_format

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


# code -> (símbolo, decimales). Las monedas sin centavos de uso corriente
# (JPY, CLP, PYG) se muestran sin decimales.
CURRENCIES = {
    "USD": ("$", 2),
    "EUR": ("€", 2),
    "JPY": ("¥", 0),
    "GBP": ("£", 2),
    "CNY": ("CN¥", 2),
    "AUD": ("A$", 2),
    "CAD": ("CA$", 2),
    "CHF": ("CHF", 2),
    "HKD": ("HK$", 2),
    "SGD": ("S$", 2),
    "MXN": ("MX$", 2),
    "COP": ("COL$", 2),
    "ARS": ("AR$", 2),
    "CLP": ("CL$", 0),
    "PEN": ("S/", 2),
    "BRL": ("R$", 2),
    "CRC": ("₡", 2),
    "GTQ": ("Q", 2),
    "HNL": ("L", 2),
    "NIO": ("C$", 2),
    "PAB": ("B/.", 2),
    "DOP": ("RD$", 2),
    "UYU": ("$U", 2),
    "BOB": ("Bs.", 2),
    "PYG": ("₲", 0),
    "VES": ("Bs.S", 2),
}


def _currency_code(context, currency=None):
    """Moneda explícita, o la de la iglesia de la petición, o USD."""
    if currency:
        return str(currency).upper()
    tenant = context.get("tenant")
    if tenant is None:
        request = context.get("request")
        user = getattr(request, "user", None)
        tenant = getattr(user, "tenant", None) or getattr(request, "tenant", None)
    return (getattr(tenant, "currency", None) or "USD").upper()


def _currency_info(code):
    symbol, decimals = CURRENCIES.get(code, (code, 2))
    return {"code": code, "symbol": symbol, "decimals": decimals}


@register.simple_tag(takes_context=True)
def money(context, amount, currency=None):
    """
    Importe con el símbolo y los decimales de la moneda y separadores del
    idioma activo: {% money x %} (moneda de la iglesia) o
    {% money donation.amount donation.currency %}.
    """
    if amount in (None, ""):
        return "-"
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return amount
    info = _currency_info(_currency_code(context, currency))
    value = round(value, info["decimals"])
    text = number_format(abs(value), decimal_pos=info["decimals"], force_grouping=True)
    return f"{'-' if value < 0 else ''}{info['symbol']}{text}"


@register.simple_tag(takes_context=True)
def currency_symbol(context, currency=None):
    return _currency_info(_currency_code(context, currency))["symbol"]


@register.simple_tag(takes_context=True)
def currency_info(context, currency=None):
    """Datos de la moneda para JS: {% currency_info as cur %}{{ cur|json_script:"id" }}"""
    return _currency_info(_currency_code(context, currency))
