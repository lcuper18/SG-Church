"""
Core views for SG Church.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View
from django.utils import timezone
from datetime import date, timedelta

from core.forms import (
    ROLE_HELP,
    ChurchSettingsForm,
    ProfileForm,
    SiteForm,
    StyledPasswordChangeForm,
    UserCreateForm,
    UserEditForm,
)
from core.mixins import ChurchAdminRequiredMixin
from emails import notify
from members.models import Member, User
from tenants.models import Tenant
from finance.models import Donation


def home(request):
    """Home page."""
    # If user is logged in and has completed onboarding, redirect to dashboard
    if request.user.is_authenticated:
        tenant = getattr(request.user, "tenant", None)
        if tenant and tenant.onboarding_completed:
            return redirect("dashboard")
        elif tenant:
            return redirect("onboarding_start")
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    """Dashboard for logged-in users."""
    user = request.user
    tenant = getattr(user, "tenant", None)

    if not tenant:
        # No tenant yet - show onboarding
        return redirect("onboarding_start")

    if not tenant.onboarding_completed:
        # Onboarding not completed
        return redirect("onboarding_start")

    # Calculate stats
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    context = {"tenant": tenant}

    # Each block is computed only for the roles that may see it; the template
    # checks the same permissions, so nothing else leaks through the numbers.
    if user.can_manage_members:
        counts = Member.objects.filter(tenant=tenant).aggregate(
            total=Count("id"),
            new_this_month=Count("id", filter=Q(created_at__gte=month_start)),
            as_member=Count("id", filter=Q(member_status="member")),
            as_visitor=Count("id", filter=Q(member_status="visitor")),
            as_attendee=Count("id", filter=Q(member_status="attendee")),
            inactive=Count("id", filter=Q(member_status="inactive")),
        )
        context.update(
            {
                "total_members": counts["total"],
                "new_members_this_month": counts["new_this_month"],
                "members_as_member": counts["as_member"],
                "members_as_visitor": counts["as_visitor"],
                "members_as_attendee": counts["as_attendee"],
                "members_inactive": counts["inactive"],
                "recent_members": Member.objects.filter(tenant=tenant).order_by(
                    "-created_at"
                )[:5],
            }
        )

    if user.can_manage_finance:
        context["donations_this_month"] = (
            Donation.objects.filter(
                tenant=tenant, status="completed", donation_date__gte=month_start
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

    return render(request, "core/dashboard.html", context)


@login_required
def profile(request):
    """Edit the user's name and change their password."""
    user = request.user
    profile_form = ProfileForm(instance=user)
    password_form = StyledPasswordChangeForm(user)

    if request.method == "POST":
        if request.POST.get("action") == "password":
            password_form = StyledPasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)  # keep the user logged in
                messages.success(request, "Contraseña actualizada.")
                return redirect("profile")
        else:
            profile_form = ProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Perfil actualizado.")
                return redirect("profile")

    return render(
        request,
        "core/profile.html",
        {"profile_form": profile_form, "password_form": password_form},
    )


class ChurchSettingsView(LoginRequiredMixin, ChurchAdminRequiredMixin, UpdateView):
    """Church-wide settings; administrators only."""

    form_class = ChurchSettingsForm
    template_name = "core/church_settings.html"
    success_url = reverse_lazy("church_settings")

    def get_object(self, queryset=None):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            raise Http404("Este usuario no pertenece a ninguna iglesia.")
        return tenant

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.object
        context["has_financial_data"] = (
            tenant.donations.exists() or tenant.expenses.exists()
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, "Configuración guardada.")
        return super().form_valid(form)


# ============================================================
# USER MANAGEMENT (church administrators)
# ============================================================


class ChurchUsersMixin(LoginRequiredMixin, ChurchAdminRequiredMixin):
    """Scope everything to the administrator's own church. Platform superusers
    are managed from /admin/, never from here."""

    def get_tenant(self):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            raise Http404("Este usuario no pertenece a ninguna iglesia.")
        return tenant

    def get_queryset(self):
        return User.objects.filter(tenant=self.get_tenant(), is_superuser=False)


class UserListView(ChurchUsersMixin, ListView):
    template_name = "core/user_list.html"
    context_object_name = "church_users"

    def get_queryset(self):
        return super().get_queryset().order_by("-is_active", "first_name", "last_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_help"] = [
            (label, ROLE_HELP[value]) for value, label in User.ROLE_CHOICES
        ]
        return context


class UserCreateView(ChurchUsersMixin, CreateView):
    form_class = UserCreateForm
    template_name = "core/user_form.html"
    success_url = reverse_lazy("user_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_help"] = ROLE_HELP
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        sent = notify.account_created(self.object, self.request)
        messages.success(
            self.request,
            f"Usuario {self.object.email} creado."
            + (" Le enviamos un correo con el enlace para elegir su contraseña." if sent else ""),
        )
        return response


class UserUpdateView(ChurchUsersMixin, UpdateView):
    form_class = UserEditForm
    template_name = "core/user_form.html"
    success_url = reverse_lazy("user_list")
    context_object_name = "target_user"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["editing_self"] = self.object.pk == self.request.user.pk
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_help"] = ROLE_HELP
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Usuario actualizado.")
        return response


class UserToggleActiveView(ChurchUsersMixin, View):
    """Activate/deactivate a login (users are never deleted from here)."""

    def post(self, request, pk):
        target = get_object_or_404(self.get_queryset(), pk=pk)
        if target.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
        else:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            messages.success(
                request,
                f"{target.get_full_name()} "
                f"{'ya puede' if target.is_active else 'ya no puede'} iniciar sesión.",
            )
        return redirect("user_list")


# ============================================================
# AUDIT TRAIL AND TRASH (church administrators)
# ============================================================


def trash_models():
    """(label_lower, model, Spanish name) for every model with a trash."""
    from core.audit import REGISTRY
    from core.softdelete import SoftDeleteModel

    return [
        (model._meta.label_lower, model, label)
        for model, label in REGISTRY.items()
        if issubclass(model, SoftDeleteModel)
    ]


class AuditLogView(LoginRequiredMixin, ChurchAdminRequiredMixin, ListView):
    """Who changed what, newest first, with simple filters."""

    template_name = "core/audit_log.html"
    context_object_name = "entries"
    paginate_by = 50

    def get_queryset(self):
        from core.models import AuditLog

        queryset = AuditLog.objects.filter(tenant=self.request.user.tenant)
        get = self.request.GET
        if get.get("model"):
            queryset = queryset.filter(model_label=get["model"])
        if get.get("action"):
            queryset = queryset.filter(action=get["action"])
        if get.get("q"):
            queryset = queryset.filter(
                Q(object_repr__icontains=get["q"]) | Q(user_label__icontains=get["q"])
            )
        start = _parse_iso_date(get.get("date_from"))
        end = _parse_iso_date(get.get("date_to"))
        if start:
            queryset = queryset.filter(created_at__date__gte=start)
        if end:
            queryset = queryset.filter(created_at__date__lte=end)
        return queryset

    def get_context_data(self, **kwargs):
        from core.audit import field_label, label_for
        from core.models import AuditLog

        context = super().get_context_data(**kwargs)
        for entry in context["entries"]:
            entry.type_label = label_for(entry.model_label)
            entry.change_rows = [
                (field_label(name), old, new) for name, (old, new) in entry.changes.items()
            ]
        context["model_choices"] = [
            (label_lower, label) for label_lower, _model, label in audited_models()
        ]
        context["action_choices"] = AuditLog.ACTION_CHOICES
        return context


def audited_models():
    from core.audit import REGISTRY

    return [(model._meta.label_lower, model, label) for model, label in REGISTRY.items()]


def _parse_iso_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class TrashView(LoginRequiredMixin, ChurchAdminRequiredMixin, TemplateView):
    """What was deleted, with the way back (or out for good)."""

    template_name = "core/trash.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.user.tenant
        groups = []
        for label_lower, model, label in trash_models():
            items = list(
                model.all_objects.filter(tenant=tenant, deleted_at__isnull=False)
                .select_related("deleted_by")
                .order_by("-deleted_at")
            )
            if items:
                groups.append({"key": label_lower, "label": label, "items": items})
        context["groups"] = groups
        context["retention_days"] = settings.TRASH_RETENTION_DAYS
        return context


class TrashActionView(LoginRequiredMixin, ChurchAdminRequiredMixin, View):
    """POST-only: restore or permanently delete one trashed record."""

    action = None  # "restore" | "purge"

    def post(self, request, model, pk):
        models_by_label = {label: m for label, m, _ in trash_models()}
        if model not in models_by_label:
            raise Http404("Tipo desconocido.")
        item = get_object_or_404(
            models_by_label[model].all_objects,
            pk=pk,
            tenant=request.user.tenant,
            deleted_at__isnull=False,
        )
        name = str(item)
        if self.action == "restore":
            try:
                with transaction.atomic():
                    item.restore(user=request.user)
            except IntegrityError:
                messages.error(
                    request,
                    f"No se puede restaurar «{name}»: ya existe otro registro con el mismo nombre o identificación. "
                    "Renombra el que está activo y vuelve a intentarlo.",
                )
            else:
                messages.success(request, f"«{name}» fue restaurado.")
        else:
            item.hard_delete(user=request.user)
            messages.success(request, f"«{name}» se eliminó definitivamente.")
        return redirect("trash")


# ============================================================
# SITES (sedes) — church administrators
# ============================================================


class SitesMixin(LoginRequiredMixin, ChurchAdminRequiredMixin):
    def get_tenant(self):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            raise Http404("Este usuario no pertenece a ninguna iglesia.")
        return tenant

    def get_queryset(self):
        from tenants.models import Site

        return Site.objects.filter(tenant=self.get_tenant())


class SiteListView(SitesMixin, ListView):
    template_name = "core/site_list.html"
    context_object_name = "sites"

    def get_queryset(self):
        from django.db.models import Count, Q

        # Reverse counts skip the manager, so trashed people/events are excluded by hand.
        return (
            super()
            .get_queryset()
            .annotate(
                member_total=Count("members", filter=Q(members__deleted_at__isnull=True), distinct=True),
                event_total=Count("events", filter=Q(events__deleted_at__isnull=True), distinct=True),
            )
        )


class SiteCreateView(SitesMixin, CreateView):
    form_class = SiteForm
    template_name = "core/site_form.html"
    success_url = reverse_lazy("site_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        return kwargs

    def form_valid(self, form):
        form.instance.tenant = self.get_tenant()
        response = super().form_valid(form)
        messages.success(self.request, f"Sede «{self.object.name}» creada.")
        return response


class SiteUpdateView(SitesMixin, UpdateView):
    form_class = SiteForm
    template_name = "core/site_form.html"
    success_url = reverse_lazy("site_list")
    context_object_name = "site"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.get_tenant()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Sede actualizada.")
        return response


class SiteDeleteView(SitesMixin, View):
    """POST-only. A site in use (main, upcoming events, members) is refused with
    the reasons and the admin is pointed at "desactivar" instead."""

    def post(self, request, pk):
        site = get_object_or_404(self.get_queryset(), pk=pk)
        reasons = site.blockers()
        if reasons:
            messages.error(
                request,
                f"No se puede eliminar «{site.name}»: {', '.join(reasons)}. "
                "Puedes desactivarla en su lugar.",
            )
        else:
            site.delete()
            messages.success(request, f"Sede «{site.name}» enviada a la papelera.")
        return redirect("site_list")
