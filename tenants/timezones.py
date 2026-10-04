"""
Time zones and per-country defaults offered when setting up a church.

The IANA names are what `Tenant.timezone` stores and what TenantMiddleware
activates on each request.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "America/New_York"

TIMEZONE_CHOICES = [
    ("America/Costa_Rica", "Costa Rica (San José)"),
    ("America/Guatemala", "Guatemala"),
    ("America/El_Salvador", "El Salvador"),
    ("America/Tegucigalpa", "Honduras (Tegucigalpa)"),
    ("America/Managua", "Nicaragua (Managua)"),
    ("America/Panama", "Panamá"),
    ("America/Mexico_City", "México (Ciudad de México)"),
    ("America/Havana", "Cuba (La Habana)"),
    ("America/Santo_Domingo", "República Dominicana"),
    ("America/Puerto_Rico", "Puerto Rico"),
    ("America/Bogota", "Colombia (Bogotá)"),
    ("America/Caracas", "Venezuela (Caracas)"),
    ("America/Guayaquil", "Ecuador (Guayaquil)"),
    ("America/Lima", "Perú (Lima)"),
    ("America/La_Paz", "Bolivia (La Paz)"),
    ("America/Santiago", "Chile (Santiago)"),
    ("America/Argentina/Buenos_Aires", "Argentina (Buenos Aires)"),
    ("America/Montevideo", "Uruguay (Montevideo)"),
    ("America/Asuncion", "Paraguay (Asunción)"),
    ("America/Sao_Paulo", "Brasil (São Paulo)"),
    ("America/New_York", "EE. UU. - Este"),
    ("America/Chicago", "EE. UU. - Centro"),
    ("America/Denver", "EE. UU. - Montaña"),
    ("America/Phoenix", "EE. UU. - Arizona"),
    ("America/Los_Angeles", "EE. UU. - Pacífico"),
    ("America/Toronto", "Canadá (Toronto)"),
    ("Europe/Madrid", "España (Madrid)"),
    ("Africa/Malabo", "Guinea Ecuatorial (Malabo)"),
    ("UTC", "UTC"),
]

# country code -> (time zone, currency) pre-selected in the onboarding form.
COUNTRY_DEFAULTS = {
    "AR": ("America/Argentina/Buenos_Aires", "ARS"),
    "BO": ("America/La_Paz", "BOB"),
    "BR": ("America/Sao_Paulo", "BRL"),
    "CA": ("America/Toronto", "CAD"),
    "CL": ("America/Santiago", "CLP"),
    "CO": ("America/Bogota", "COP"),
    "CR": ("America/Costa_Rica", "CRC"),
    "CU": ("America/Havana", "USD"),
    "DO": ("America/Santo_Domingo", "DOP"),
    "EC": ("America/Guayaquil", "USD"),
    "ES": ("Europe/Madrid", "EUR"),
    "GQ": ("Africa/Malabo", "USD"),
    "GT": ("America/Guatemala", "GTQ"),
    "HN": ("America/Tegucigalpa", "HNL"),
    "MX": ("America/Mexico_City", "MXN"),
    "NI": ("America/Managua", "NIO"),
    "PA": ("America/Panama", "PAB"),
    "PE": ("America/Lima", "PEN"),
    "PR": ("America/Puerto_Rico", "USD"),
    "PY": ("America/Asuncion", "PYG"),
    "SV": ("America/El_Salvador", "USD"),
    "US": ("America/New_York", "USD"),
    "UY": ("America/Montevideo", "UYU"),
    "VE": ("America/Caracas", "VES"),
}


def get_zone(name):
    """ZoneInfo for an IANA name, or None when the name is empty or unknown."""
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None


def defaults_for_country(country):
    """(timezone, currency) suggested for a country code."""
    return COUNTRY_DEFAULTS.get(country or "", (DEFAULT_TIMEZONE, "USD"))
