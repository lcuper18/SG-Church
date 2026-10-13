"""CSV exports that open correctly in Excel.

- UTF-8 with a BOM, so Excel shows accents instead of mojibake.
- Dates in the church's own time zone (the request's active zone), ISO format.
- Text cells that start with = + - @ are prefixed with an apostrophe so a
  spreadsheet never evaluates user-entered text as a formula (CSV injection:
  a member called "=HYPERLINK(...)" must not run when staff open the file).
"""

import csv
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def cell(value):
    """Convert one value to a safe CSV cell."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    return f"'{text}" if text.startswith(_FORMULA_PREFIXES) else text


def csv_response(filename, header, rows):
    """Build a downloadable CSV response from a header row and an iterable of
    row sequences."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow([cell(value) for value in row])
    return response


def export_filename(prefix):
    return f"{prefix}-{timezone.localdate().isoformat()}.csv"
