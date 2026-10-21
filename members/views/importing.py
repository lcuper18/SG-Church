"""Importing members from a CSV file."""

import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.generic import View

from core.exports import csv_response
from core.mixins import ManageMembersRequiredMixin

from .. import importer


def _import_dir():
    path = Path(settings.IMPORT_TMP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _forget_old_uploads(max_age_seconds=3600):
    cutoff = time.time() - max_age_seconds
    for path in _import_dir().glob("*.csv"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


class MemberImportView(ManageMembersRequiredMixin, View):
    """Step 1: upload the file and see what would happen. Nothing is saved."""

    def get(self, request):
        return render(request, "members/import.html", self._context())

    def post(self, request):
        upload = request.FILES.get("file")
        policy = "update" if request.POST.get("policy") == "update" else "skip"
        if upload is None:
            return render(
                request, "members/import.html",
                self._context(error="Elige un archivo CSV para continuar."),
            )
        tenant = request.user.tenant
        try:
            raw = upload.read(importer.MAX_BYTES + 1)
            plan = importer.build_plan(
                raw, tenant, policy=policy, can_see_notes=request.user.can_view_pastoral_notes
            )
        except importer.ImportFileError as error:
            return render(request, "members/import.html", self._context(error=str(error)))

        _forget_old_uploads()
        token = uuid.uuid4().hex
        (_import_dir() / f"{token}.csv").write_bytes(raw)
        request.session["member_import"] = {
            "token": token, "policy": policy, "tenant": str(tenant.pk), "name": upload.name,
        }
        return render(
            request, "members/import_preview.html",
            {
                "plan": plan,
                "token": token,
                "filename": upload.name,
                "problem_rows": [r for r in plan.rows if r.action in ("error", "skip") or r.warnings][:100],
                "sample_rows": [r for r in plan.rows if r.action in ("create", "update")][:15],
                "field_labels": [importer.name_label(n) for n in plan.columns],
            },
        )

    @staticmethod
    def _context(error=None):
        return {"error": error, "max_mb": importer.MAX_BYTES // (1024 * 1024), "max_rows": importer.MAX_ROWS}


member_import = MemberImportView.as_view()


class MemberImportConfirmView(ManageMembersRequiredMixin, View):
    """Step 2: do it. The file is read and checked again so the result matches
    the church's data at this moment, not at preview time."""

    def post(self, request):
        pending = request.session.get("member_import")
        tenant = request.user.tenant
        if (
            not pending
            or pending.get("token") != request.POST.get("token")
            or pending.get("tenant") != str(tenant.pk)
        ):
            messages.error(request, "La importación venció. Sube el archivo de nuevo.")
            return redirect("member_import")
        path = _import_dir() / f"{pending['token']}.csv"
        if not path.exists():
            messages.error(request, "La importación venció. Sube el archivo de nuevo.")
            return redirect("member_import")

        plan = importer.build_plan(
            path.read_bytes(), tenant, policy=pending["policy"],
            can_see_notes=request.user.can_view_pastoral_notes,
        )
        counters = importer.apply_plan(plan, tenant, request.user)
        path.unlink(missing_ok=True)
        request.session.pop("member_import", None)

        parts = [f"{counters['created']} nuevos"]
        if counters["updated"]:
            parts.append(f"{counters['updated']} actualizados")
        if counters["skipped"]:
            parts.append(f"{counters['skipped']} omitidos")
        if counters["errors"]:
            parts.append(f"{counters['errors']} con errores (no se importaron)")
        extra = []
        if counters["families_created"]:
            extra.append(f"{counters['families_created']} familias creadas")
        if counters["tags_created"]:
            extra.append(f"{counters['tags_created']} etiquetas creadas")
        messages.success(
            request, "Importación lista: " + ", ".join(parts) + (f" ({', '.join(extra)})" if extra else "") + "."
        )
        return redirect("member_list")


member_import_confirm = MemberImportConfirmView.as_view()


@login_required
def member_import_template(request):
    """A CSV with the expected columns and one example row."""
    if not request.user.can_manage_members:
        raise PermissionDenied
    return csv_response("plantilla-miembros.csv", importer.TEMPLATE_HEADER, [importer.TEMPLATE_EXAMPLE])
