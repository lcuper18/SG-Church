"""
Import members from a CSV file (a spreadsheet saved as CSV).

Two phases so nothing is changed blindly:

1. `build_plan()` reads and validates the whole file and says, row by row, what
   would happen (create / update / skip / error) -- the preview.
2. `apply_plan()` performs it in one transaction.

The file may be the export of this same system (round trip), or a church's own
spreadsheet: header names are matched loosely (case, accents, common synonyms),
delimiters `,` `;` and tab are detected, UTF-8 (with or without BOM) and Excel's
Windows-1252 are both read, and dates may be `2026-10-17` or `17/10/2026`.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from core import audit
from core.text import fold
from members.models import Family, Member, Tag

MAX_ROWS = 5000
MAX_BYTES = 2 * 1024 * 1024

# Header (folded) -> field. Several spellings per field.
COLUMN_ALIASES = {
    "first_name": ["nombre", "nombres", "first name", "first_name", "primer nombre"],
    "last_name": ["apellido", "apellidos", "last name", "last_name"],
    "email": ["email", "e-mail", "correo", "correo electronico", "mail"],
    "phone": ["telefono", "tel", "celular", "movil", "phone", "telefono celular"],
    "national_id": [
        "identificacion", "cedula", "cedula de identidad", "documento", "documento de identidad", "dni",
        "id", "numero de identificacion", "national id", "national_id", "curp", "rut", "dui", "cpf",
    ],
    "date_of_birth": [
        "fecha de nacimiento", "nacimiento", "cumpleanos", "fecha nacimiento",
        "birth date", "date of birth", "date_of_birth",
    ],
    "gender": ["genero", "sexo", "gender"],
    "marital_status": ["estado civil", "marital status", "marital_status"],
    "is_baptized": ["bautizado", "bautizada", "bautizado/a", "baptized", "is_baptized"],
    "baptism_date": ["fecha de bautismo", "bautismo", "baptism date", "baptism_date"],
    "member_status": ["estado", "estatus", "condicion", "status", "member_status"],
    "membership_date": ["fecha de membresia", "membresia", "membership date", "membership_date"],
    "family": ["familia", "family"],
    "address": ["direccion", "address", "domicilio"],
    "city": ["ciudad", "city", "canton", "localidad"],
    "state": ["estado/provincia", "provincia", "departamento", "state", "region"],
    "postal_code": ["codigo postal", "cp", "postal code", "postal_code", "zip"],
    "tags": ["etiquetas", "etiqueta", "tags", "grupos", "ministerios"],
    "notes": ["notas", "notes", "observaciones", "comentarios"],
}
ALIAS_TO_FIELD = {fold(a): f for f, aliases in COLUMN_ALIASES.items() for a in aliases}

TEMPLATE_HEADER = [
    "Nombre", "Apellido", "Email", "Teléfono", "Identificación", "Fecha de nacimiento", "Género",
    "Estado civil", "Bautizado", "Fecha de bautismo", "Estado", "Fecha de membresía", "Familia", "Dirección",
    "Ciudad", "Estado/Provincia", "Código postal", "Etiquetas",
]
TEMPLATE_EXAMPLE = [
    "María", "Rodríguez Mora", "maria@ejemplo.com", "+506 8888 1234", "1-1234-5678", "1990-05-17",
    "Femenino", "Casado/a", "Sí", "2010-08-01", "Miembro", "2012-03-04", "Familia Rodríguez",
    "100 m norte de la iglesia", "San José", "San José", "10101", "Jóvenes, Alabanza",
]

CHOICE_WORDS = {
    "gender": {
        "male": ["masculino", "hombre", "varon", "m", "male"],
        "female": ["femenino", "mujer", "f", "female"],
        "other": ["otro", "otra", "other"],
    },
    "marital_status": {
        "single": ["soltero", "soltera", "soltero/a", "single"],
        "married": ["casado", "casada", "casado/a", "married"],
        "divorced": ["divorciado", "divorciada", "divorciado/a", "divorced"],
        "widowed": ["viudo", "viuda", "viudo/a", "widowed"],
    },
    "member_status": {
        "visitor": ["visitante", "visita", "visitor"],
        "attendee": ["asistente", "asiste", "attendee"],
        "member": ["miembro", "member"],
        "inactive": ["inactivo", "inactiva", "inactive"],
    },
}
CHOICE_LOOKUP = {
    field_name: {fold(word): code for code, words in words_by_code.items() for word in words}
    for field_name, words_by_code in CHOICE_WORDS.items()
}
CHOICE_LABELS = {
    "gender": "masculino, femenino u otro",
    "marital_status": "soltero/a, casado/a, divorciado/a o viudo/a",
    "member_status": "visitante, asistente, miembro o inactivo",
}

TRUE_WORDS = {"si", "s", "yes", "y", "true", "1", "x", "verdadero"}
FALSE_WORDS = {"no", "n", "false", "0", "falso"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d")
TAG_SPLIT = re.compile(r"[;,|]")


class ImportFileError(Exception):
    """The file can't be read at all (empty, too big, no usable header)."""


@dataclass
class RowResult:
    number: int  # spreadsheet row (header is row 1)
    data: dict
    action: str  # create | update | skip | error
    messages: list = field(default_factory=list)
    existing_id: str = ""
    tags: list = field(default_factory=list)
    family: str = ""

    @property
    def label(self):
        return f"{self.data.get('first_name', '')} {self.data.get('last_name', '')}".strip()


@dataclass
class ImportPlan:
    rows: list
    columns: list  # recognised field names in file order
    ignored_headers: list
    policy: str

    def count(self, action):
        return sum(1 for r in self.rows if r.action == action)

    @property
    def count_create(self):
        return self.count("create")

    @property
    def count_update(self):
        return self.count("update")

    @property
    def count_skip(self):
        return self.count("skip")

    @property
    def count_error(self):
        return self.count("error")

    @property
    def errors(self):
        return [r for r in self.rows if r.action == "error"]

    @property
    def importable(self):
        return self.count("create") + self.count("update")


def decode(raw):
    if len(raw) > MAX_BYTES:
        raise ImportFileError(f"El archivo es demasiado grande (máximo {MAX_BYTES // (1024 * 1024)} MB).")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportFileError("No se pudo leer el archivo. Guárdalo como CSV (UTF-8) e inténtalo de nuevo.")


def _unprotect(text):
    """Undo the apostrophe our exports put before text starting with = + - @
    (so '+506... comes back as +506...)."""
    if len(text) > 1 and text[0] == "'" and text[1] in "=+-@\t\r":
        return text[1:]
    return text


def _read_rows(text):
    lines = text.splitlines()
    if not lines or not "".join(lines).strip():
        raise ImportFileError("El archivo está vacío.")
    sample = "\n".join(lines[:5])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.reader(io.StringIO(text), dialect))


def _parse_date(value):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _clean_row(raw, columns, can_see_notes):
    """Return (data, tags, family, messages) for one row."""
    data, messages, tags, family = {}, [], [], ""
    for index, name in columns:
        value = _unprotect((raw[index] if index < len(raw) else "").strip())
        if name == "notes" and not can_see_notes:
            continue
        if name == "tags":
            tags = [t.strip() for t in TAG_SPLIT.split(value) if t.strip()]
            too_long = [t for t in tags if len(t) > 50]
            if too_long:
                messages.append(f"Etiqueta demasiado larga (máximo 50 caracteres): {too_long[0][:30]}…")
        elif name == "family":
            family = value
            limit = Family._meta.get_field("name").max_length
            if len(family) > limit:
                messages.append(f"El nombre de la familia es demasiado largo ({len(family)} de {limit}).")
        elif name in ("date_of_birth", "baptism_date", "membership_date"):
            if value:
                parsed = _parse_date(value)
                if parsed is None:
                    messages.append(f"Fecha no válida en «{name_label(name)}»: {value} (usa 2026-10-17 o 17/10/2026).")
                elif parsed > date.today() and name != "membership_date":
                    messages.append(f"«{name_label(name)}» está en el futuro: {value}.")
                else:
                    data[name] = parsed
        elif name == "is_baptized":
            word = fold(value)
            if word in TRUE_WORDS:
                data[name] = True
            elif word in FALSE_WORDS:
                data[name] = False
            elif word:
                messages.append(f"«Bautizado» debe ser Sí o No (llegó: {value}).")
        elif name in CHOICE_LOOKUP:
            if value:
                code = CHOICE_LOOKUP[name].get(fold(value))
                if code is None:
                    messages.append(f"«{name_label(name)}» no reconocido: {value} (use {CHOICE_LABELS[name]}).")
                else:
                    data[name] = code
        elif name == "email":
            if value:
                try:
                    validate_email(value)
                    data[name] = value.lower()
                except ValidationError:
                    messages.append(f"Correo no válido: {value}.")
        else:
            limit = Member._meta.get_field(name).max_length
            if limit and len(value) > limit:
                messages.append(f"«{name_label(name)}» es demasiado largo ({len(value)} de {limit} caracteres).")
            elif value or name in ("first_name", "last_name"):
                data[name] = value
    for required, label in (("first_name", "Nombre"), ("last_name", "Apellido")):
        if not data.get(required):
            messages.append(f"Falta el {label}.")
    return data, tags, family, messages


def name_label(field_name):
    return {
        "first_name": "Nombre", "last_name": "Apellido", "email": "Email", "phone": "Teléfono", "national_id": "Identificación",
        "date_of_birth": "Fecha de nacimiento", "gender": "Género", "marital_status": "Estado civil",
        "is_baptized": "Bautizado", "baptism_date": "Fecha de bautismo", "member_status": "Estado",
        "membership_date": "Fecha de membresía", "family": "Familia", "address": "Dirección",
        "city": "Ciudad", "state": "Estado/Provincia", "postal_code": "Código postal",
        "tags": "Etiquetas", "notes": "Notas",
    }.get(field_name, field_name)


def _find_existing(tenant):
    """Lookups of the church's live members to detect duplicates."""
    by_email, by_identity, by_id = {}, {}, {}
    for member in Member.objects.filter(tenant=tenant).only(
        "id", "first_name", "last_name", "email", "phone", "date_of_birth", "national_id_key"
    ):
        if member.national_id_key:
            by_id.setdefault(member.national_id_key, member)
        if member.email:
            by_email.setdefault(member.email.lower(), member)
        key = fold(f"{member.first_name} {member.last_name}")
        by_identity.setdefault(key, []).append(member)
    return by_email, by_identity, by_id


def _match(data, by_email, by_identity, by_id):
    """The existing member this row is about, if any. The national ID is the
    surest sign (two people can share a name, even an e-mail address), then the
    e-mail, then name plus phone or birth date."""
    id_key = Member.normalize_national_id(data.get("national_id"))
    if id_key and id_key in by_id:
        return by_id[id_key]
    email = data.get("email")
    if email and email in by_email:
        return by_email[email]
    if not email:
        # No e-mail to go by: the same name plus the same phone or birth date.
        for candidate in by_identity.get(fold(f"{data['first_name']} {data['last_name']}"), []):
            same_phone = data.get("phone") and data["phone"] == candidate.phone
            same_birth = data.get("date_of_birth") and data["date_of_birth"] == candidate.date_of_birth
            if same_phone or same_birth:
                return candidate
    return None


def _identity_clash(data, id_key, existing, by_email, by_id):
    """A row whose ID and e-mail point at different people, or that would give
    someone an ID that is already taken, is a mistake in the sheet: report it
    instead of guessing."""
    owner = by_id.get(id_key) if id_key else None
    email_owner = by_email.get(data.get("email")) if data.get("email") else None
    if owner and email_owner and owner.pk != email_owner.pk:
        return (
            f"La identificación pertenece a {owner.first_name} {owner.last_name} "
            f"pero el correo pertenece a {email_owner.first_name} {email_owner.last_name}."
        )
    if id_key and existing is not None and not owner and existing.national_id_key \
            and existing.national_id_key != id_key:
        return (
            f"{existing.first_name} {existing.last_name} ya tiene otra identificación registrada; "
            "revisa el número."
        )
    return ""


def build_plan(raw, tenant, policy="skip", can_see_notes=False):
    """Read, validate and classify every row. Nothing is saved."""
    rows = _read_rows(decode(raw))
    header = rows[0]
    # Keep each row's number in the sheet (header = 1) even when blank lines are skipped.
    body = [(number, r) for number, r in enumerate(rows[1:], start=2) if any(c.strip() for c in r)]

    columns, ignored, seen = [], [], set()
    for index, title in enumerate(header):
        name = ALIAS_TO_FIELD.get(fold(title.strip().lstrip("﻿")))
        if name and name not in seen:
            columns.append((index, name))
            seen.add(name)
        elif title.strip():
            ignored.append(title.strip())
    if "notes" in seen and not can_see_notes:
        ignored.append("Notas (solo administradores y pastores pueden importarlas)")
    missing = [name_label(n) for n in ("first_name", "last_name") if n not in seen]
    if missing:
        raise ImportFileError(
            "Faltan columnas obligatorias: " + " y ".join(missing)
            + ". La primera fila debe tener los títulos de las columnas (puedes descargar la plantilla)."
        )
    if not body:
        raise ImportFileError("El archivo solo tiene los títulos, sin ninguna persona.")
    if len(body) > MAX_ROWS:
        raise ImportFileError(f"Demasiadas filas ({len(body)}); el máximo por archivo es {MAX_ROWS}.")

    by_email, by_identity, by_id = _find_existing(tenant)
    seen_in_file = set()
    results = []
    for number, raw_row in body:
        data, tags, family, messages = _clean_row(raw_row, columns, can_see_notes)
        result = RowResult(number=number, data=data, action="error", messages=messages,
                           tags=tags, family=family)
        if not messages:
            id_key = Member.normalize_national_id(data.get("national_id"))
            key = ("id:" + id_key) if id_key else (data.get("email") or fold(
                f"{data['first_name']} {data['last_name']} {data.get('phone', '')} {data.get('date_of_birth', '')}"
            ))
            existing = _match(data, by_email, by_identity, by_id)
            clash = _identity_clash(data, id_key, existing, by_email, by_id)
            if clash:
                result.messages = [clash]
            elif key in seen_in_file:
                result.action, result.messages = "skip", ["Repetido dentro del mismo archivo."]
            elif existing is not None:
                result.existing_id = str(existing.pk)
                if policy == "update":
                    result.action = "update"
                else:
                    result.action, result.messages = "skip", ["Ya existe en tu iglesia."]
            else:
                result.action = "create"
            seen_in_file.add(key)
        results.append(result)
    return ImportPlan(rows=results, columns=[n for _, n in columns], ignored_headers=ignored, policy=policy)


def _get_family(tenant, name, cache, counters):
    if not name:
        return None
    key = fold(name)
    if key not in cache:
        existing = next(
            (f for f in Family.objects.filter(tenant=tenant) if fold(f.name) == key), None
        )
        if existing is None:
            existing = Family.objects.create(tenant=tenant, name=name)
            counters["families_created"] += 1
        cache[key] = existing
    return cache[key]


def _get_tags(tenant, names, cache, counters):
    found = []
    for name in names:
        key = fold(name)
        if key not in cache:
            existing = next((t for t in Tag.objects.filter(tenant=tenant) if fold(t.name) == key), None)
            if existing is None:
                existing = Tag.objects.create(tenant=tenant, name=name[:50])
                counters["tags_created"] += 1
            cache[key] = existing
        found.append(cache[key])
    return found


@transaction.atomic
def apply_plan(plan, tenant, user):
    """Perform the plan. One audit line summarises the import instead of one
    per person."""
    counters = {"created": 0, "updated": 0, "skipped": 0, "errors": 0,
                "families_created": 0, "tags_created": 0}
    family_cache, tag_cache = {}, {}
    with audit.suppressed():
        for row in plan.rows:
            if row.action == "error":
                counters["errors"] += 1
                continue
            if row.action == "skip":
                counters["skipped"] += 1
                continue
            family = _get_family(tenant, row.family, family_cache, counters)
            tags = _get_tags(tenant, row.tags, tag_cache, counters)
            if row.action == "create":
                member = Member(tenant=tenant, **row.data)
                if family:
                    member.family = family
                member.save()
                counters["created"] += 1
            else:
                member = Member.objects.get(pk=row.existing_id, tenant=tenant)
                for name, value in row.data.items():
                    setattr(member, name, value)  # only what the file provides
                if family:
                    member.family = family
                member.save()
                counters["updated"] += 1
            if tags:
                member.tags.add(*tags)
    audit.log_note(
        tenant, user, "import", "members.member",
        f"Importación CSV: {counters['created']} nuevos, {counters['updated']} actualizados, "
        f"{counters['skipped']} omitidos",
    )
    return counters
