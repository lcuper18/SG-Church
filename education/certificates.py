"""
PDF for a block certificate (landscape Letter, drawn with ReportLab: pure
Python, nothing to install on the server).

The certificate carries a QR code and a short URL that anyone can open to check
it is genuine (`certificate_verify`), so a printed copy can't simply be forged.
Built-in PDF fonts only cover Latin text; characters outside it are replaced
with "?" instead of failing.
"""

import io
import logging

from django.utils import timezone
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
]
INK = HexColor("#1f2937")
MUTED = HexColor("#6b7280")
BRAND = HexColor("#1f3a5f")
GOLD = HexColor("#b08d3c")


def long_date(value):
    return f"{value.day} de {MONTHS[value.month - 1]} de {value.year}"


def _safe(text):
    return str(text or "").encode("cp1252", "replace").decode("cp1252")


def _fit(text, font, size, max_width, minimum=14):
    """Largest size (down to `minimum`) at which `text` fits `max_width`."""
    while size > minimum and stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _centered(pdf, x, y, text, font, size, color=INK, spacing=0):
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    if spacing:
        text_object = pdf.beginText()
        text_object.setTextOrigin(x - (stringWidth(text, font, size) + spacing * len(text)) / 2, y)
        text_object.setFont(font, size)
        text_object.setCharSpace(spacing)
        text_object.textOut(text)
        text_object.setCharSpace(0)  # the setting would otherwise leak into every later line
        pdf.drawText(text_object)
    else:
        pdf.drawCentredString(x, y, text)


def _logo(tenant):
    """The church's logo as an ImageReader, or None (missing, unreadable...)."""
    if not tenant.logo:
        return None
    try:
        with tenant.logo.open("rb") as handle:
            return ImageReader(io.BytesIO(handle.read()))
    except Exception:  # noqa: BLE001 - a broken logo must not block the certificate
        logger.warning("Could not read the logo of %s", tenant.pk, exc_info=True)
        return None


def render_certificate_pdf(certificate, verify_url=""):
    """Return the certificate as PDF bytes."""
    tenant, member, block = certificate.tenant, certificate.member, certificate.course_block
    issued = timezone.localtime(certificate.issued_at).date()
    width, height = landscape(letter)
    middle = width / 2

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    pdf.setTitle(_safe(f"Certificado - {block.name} - {member.full_name}"))
    pdf.setAuthor(_safe(tenant.name))
    pdf.setSubject(_safe(f"Certificado {certificate.certificate_number}"))

    # Frame: a heavy outer line, a fine inner one, small gold corners.
    pdf.setStrokeColor(BRAND)
    pdf.setLineWidth(4)
    pdf.rect(30, 30, width - 60, height - 60)
    pdf.setLineWidth(0.8)
    pdf.setStrokeColor(GOLD)
    pdf.rect(40, 40, width - 80, height - 80)

    top = height - 90
    logo = _logo(tenant)
    if logo:
        logo_width, logo_height = logo.getSize()
        scale = min(150 / logo_width, 62 / logo_height)
        pdf.drawImage(
            logo, middle - logo_width * scale / 2, top - 52, logo_width * scale, logo_height * scale,
            mask="auto",
        )
        top -= 70

    church = _safe(tenant.name)
    _centered(pdf, middle, top - 4, church, "Times-Bold", _fit(church, "Times-Bold", 26, width - 160, 16), BRAND)
    _centered(pdf, middle, top - 34, "CERTIFICADO DE FINALIZACIÓN",
              "Helvetica", 11, MUTED, spacing=3)

    _centered(pdf, middle, top - 78, "Se certifica que", "Times-Italic", 15, MUTED)
    name = _safe(member.full_name)
    size = _fit(name, "Times-BoldItalic", 40, width - 170)
    _centered(pdf, middle, top - 126, name, "Times-BoldItalic", size, INK)
    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(0.8)
    half = min(max(200, stringWidth(name, "Times-BoldItalic", size) / 2 + 12), middle - 70)
    pdf.line(middle - half, top - 138, middle + half, top - 138)
    if member.national_id:
        _centered(
            pdf, middle, top - 154, _safe(f"{tenant.id_label}: {member.national_id}"),
            "Helvetica", 11, MUTED,
        )

    _centered(pdf, middle, top - 182, "completó satisfactoriamente todos los cursos del bloque",
              "Times-Roman", 15, INK)
    block_name = _safe(block.name)
    block_size = _fit(block_name, "Times-Bold", 26, width - 170, 14)
    _centered(pdf, middle, top - 216, block_name, "Times-Bold", block_size, BRAND)

    courses = [
        _safe(c.title) for c in block.courses.filter(is_active=True).order_by("order_in_block", "title")
    ]
    if courses:
        listing = "Cursos: " + "  ·  ".join(courses)
        y = top - 244
        for line in simpleSplit(listing, "Helvetica", 9.5, width - 200)[:3]:
            _centered(pdf, middle, y, line, "Helvetica", 9.5, MUTED)
            y -= 13

    # Signature (left) and issue date (right).
    base = 118
    signer_name = _safe(getattr(tenant, "certificate_signer_name", "") or "")
    signer_title = _safe(getattr(tenant, "certificate_signer_title", "") or "")
    pdf.setStrokeColor(INK)
    pdf.setLineWidth(0.7)
    pdf.line(middle - 250, base, middle - 60, base)
    if signer_name:
        _centered(pdf, middle - 155, base - 14, signer_name, "Times-Bold", 12, INK)
    _centered(pdf, middle - 155, base - (28 if signer_name else 14), signer_title or "Firma autorizada",
              "Times-Roman", 10.5, MUTED)
    pdf.line(middle + 60, base, middle + 250, base)
    _centered(pdf, middle + 155, base - 14, _safe(long_date(issued)), "Times-Bold", 12, INK)
    _centered(pdf, middle + 155, base - 28, "Fecha de emisión", "Times-Roman", 10.5, MUTED)

    # Footer: number, where to verify, QR.
    _centered(pdf, middle, 66, f"N.º de certificado: {certificate.certificate_number}", "Helvetica-Bold", 9, INK)
    if verify_url:
        _centered(pdf, middle, 54, _safe(f"Verifica su autenticidad en {verify_url}"), "Helvetica", 7.5, MUTED)
        qr = QrCodeWidget(verify_url)
        x0, y0, x1, y1 = qr.getBounds()
        side = 62
        drawing = Drawing(side, side, transform=[side / (x1 - x0), 0, 0, side / (y1 - y0), 0, 0])
        drawing.add(qr)
        renderPDF.draw(drawing, pdf, width - 50 - side - 8, 50)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
