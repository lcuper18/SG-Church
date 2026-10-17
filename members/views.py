"""
Member, Family, and Tag views.
"""

import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    View,
)

from core.exports import csv_response, export_filename
from core.mixins import ManageMembersRequiredMixin
from django.contrib.auth import login
from django.db import models
from django.urls import reverse, reverse_lazy
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from .forms import FamilyForm, MyContactForm
from .search import search_members
from .models import Member, Family, Tag
from tenants.models import Tenant
from tenants.timezones import (
    DEFAULT_TIMEZONE,
    TIMEZONE_CHOICES,
    defaults_for_country,
    get_zone,
)
from members.models import User


# ============================================================
# ONBOARDING VIEWS
# ============================================================


class OnboardingStartView(TemplateView):
    """Start page for onboarding wizard."""

    template_name = "onboarding/start.html"

    def dispatch(self, request, *args, **kwargs):
        # If user is already logged in and has completed onboarding, redirect to dashboard
        if request.user.is_authenticated:
            tenant = getattr(request.user, "tenant", None)
            if tenant and tenant.onboarding_completed:
                return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class OnboardingChurchView(View):
    """Step 1: Church information."""

    template_name = "onboarding/church.html"

    def get(self, request):
        # Check if previous step is complete (not applicable for step 1)
        return render(
            request,
            self.template_name,
            {"country_choices": Tenant.COUNTRY_CHOICES},
        )

    def post(self, request):
        # Store church info in session
        request.session["onboarding_church"] = {
            "name": request.POST.get("name"),
            "denomination": request.POST.get("denomination"),
            "country": request.POST.get("country"),
            "city": request.POST.get("city"),
            "state": request.POST.get("state"),
            "address": request.POST.get("address"),
            "phone": request.POST.get("phone"),
        }
        return redirect("onboarding_admin")


class OnboardingAdminView(View):
    """Step 2: Create admin user."""

    template_name = "onboarding/admin.html"

    def get(self, request):
        # Check if previous step is complete
        if "onboarding_church" not in request.session:
            return redirect("onboarding_church")
        return render(request, self.template_name)

    def post(self, request):
        if "onboarding_church" not in request.session:
            return redirect("onboarding_church")

        # Validate
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password_confirm = request.POST.get("password_confirm")
        terms = request.POST.get("terms")

        errors = []
        if not first_name:
            errors.append("First name is required")
        if not last_name:
            errors.append("Last name is required")
        if not email:
            errors.append("Email is required")
        if not password:
            errors.append("Password is required")
        if password != password_confirm:
            errors.append("Passwords do not match")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if not terms:
            errors.append("You must accept the terms and conditions")

        if errors:
            return render(
                request,
                self.template_name,
                {"errors": errors, "data": request.POST},
            )

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return render(
                request,
                self.template_name,
                {"errors": ["Email already exists"], "data": request.POST},
            )

        # Store admin info in session
        request.session["onboarding_admin"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
        }

        return redirect("onboarding_settings")


class OnboardingSettingsView(View):
    """Step 3: Basic settings."""

    template_name = "onboarding/settings.html"

    def get(self, request):
        # Check if previous steps are complete
        if "onboarding_church" not in request.session:
            return redirect("onboarding_church")
        if "onboarding_admin" not in request.session:
            return redirect("onboarding_admin")
        country = request.session["onboarding_church"].get("country")
        selected_timezone, selected_currency = defaults_for_country(country)
        return render(
            request,
            self.template_name,
            {
                "currency_choices": Tenant.CURRENCY_CHOICES,
                "timezone_choices": TIMEZONE_CHOICES,
                "selected_currency": selected_currency,
                "selected_timezone": selected_timezone,
            },
        )

    def post(self, request):
        if "onboarding_church" not in request.session:
            return redirect("onboarding_church")
        if "onboarding_admin" not in request.session:
            return redirect("onboarding_admin")

        # Store settings in session
        request.session["onboarding_settings"] = {
            "currency": request.POST.get("currency", "USD"),
            "timezone": (
                request.POST.get("timezone")
                if get_zone(request.POST.get("timezone"))
                else DEFAULT_TIMEZONE
            ),
            "date_format": request.POST.get("date_format", "DD/MM/YYYY"),
            "enable_families": request.POST.get("enable_families") == "on",
            "enable_tags": request.POST.get("enable_tags") == "on",
        }

        return redirect("onboarding_complete_setup")


class OnboardingCompleteView(View):
    """Step 4: Complete onboarding and create tenant/user."""

    template_name = "onboarding/complete.html"

    def get(self, request):
        # Check if previous steps are complete
        if "onboarding_church" not in request.session:
            return redirect("onboarding_church")
        if "onboarding_admin" not in request.session:
            return redirect("onboarding_admin")
        if "onboarding_settings" not in request.session:
            return redirect("onboarding_settings")

        # Get session data
        church_data = request.session["onboarding_church"]
        admin_data = request.session["onboarding_admin"]
        settings_data = request.session["onboarding_settings"]

        # Generate subdomain from church name
        import re

        subdomain = re.sub(r"[^a-z0-9]", "", church_data.get("name", "").lower())[:50]
        # Make unique
        base_subdomain = subdomain
        counter = 1
        while Tenant.objects.filter(subdomain=subdomain).exists():
            subdomain = f"{base_subdomain}{counter}"
            counter += 1

        # Create tenant
        tenant = Tenant.objects.create(
            name=church_data.get("name", ""),
            subdomain=subdomain,
            denomination=church_data.get("denomination", ""),
            country=church_data.get("country", ""),
            city=church_data.get("city", ""),
            state=church_data.get("state", ""),
            address=church_data.get("address", ""),
            phone=church_data.get("phone", ""),
            email=admin_data.get("email", ""),
            currency=settings_data.get("currency", "USD"),
            timezone=settings_data.get("timezone", "America/New_York"),
            date_format=settings_data.get("date_format", "DD/MM/YYYY"),
            enable_families=settings_data.get("enable_families", True),
            enable_tags=settings_data.get("enable_tags", True),
            onboarding_completed=True,
        )

        # Create admin user
        user = User.objects.create_user(
            username=admin_data.get("email", "").split("@")[0],
            email=admin_data.get("email", ""),
            first_name=admin_data.get("first_name", ""),
            last_name=admin_data.get("last_name", ""),
            password=admin_data.get("password", ""),
            role="admin",
            tenant=tenant,
        )

        # Log the user in (specify backend to avoid multiple backends error)
        from django.contrib.auth.backends import ModelBackend

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        # Clear session
        del request.session["onboarding_church"]
        del request.session["onboarding_admin"]
        del request.session["onboarding_settings"]

        messages.success(request, f"Welcome to {tenant.name}!")
        return redirect("dashboard")


# ============================================================
# MEMBER VIEWS
# ============================================================


def filtered_members(request):
    """The tenant's members narrowed by the list page's query-string filters
    (shared by the list and its CSV export)."""
    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        return Member.objects.none()

    queryset = Member.objects.filter(tenant=tenant)

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(member_status=status)

    family_id = request.GET.get("family")
    if family_id:
        queryset = queryset.filter(family_id=family_id)

    tag_id = request.GET.get("tag")
    if tag_id:
        queryset = queryset.filter(tags__id=tag_id)

    search = request.GET.get("search")
    if search:
        queryset = search_members(queryset, search)

    return (
        queryset.select_related("family")
        .prefetch_related("tags")
        .order_by("last_name", "first_name")
    )


class MemberListView(ManageMembersRequiredMixin, ListView):
    """List all members with filtering and search."""

    model = Member
    template_name = "members/list.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        return filtered_members(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if tenant:
            context["families"] = Family.objects.filter(tenant=tenant)
            context["tags"] = Tag.objects.filter(tenant=tenant)

        return context


member_list = MemberListView.as_view()


class MemberExportView(ManageMembersRequiredMixin, View):
    """Download the members matching the list's current filters. Restricted to
    roles that manage members: the file carries phones, addresses and birth
    dates for the whole directory."""

    def get(self, request):
        header = [
            "Nombre", "Apellido", "Email", "Teléfono", "Fecha de nacimiento", "Género",
            "Estado civil", "Bautizado", "Fecha de bautismo", "Estado", "Fecha de membresía",
            "Familia", "Dirección", "Ciudad", "Estado/Provincia", "Código postal", "Etiquetas",
        ]
        rows = (
            [
                m.first_name, m.last_name, m.email, m.phone, m.date_of_birth,
                m.get_gender_display(), m.get_marital_status_display(), m.is_baptized,
                m.baptism_date, m.get_member_status_display(), m.membership_date,
                m.family.name if m.family else "", m.address, m.city, m.state,
                m.postal_code, ", ".join(t.name for t in m.tags.all()),
            ]
            for m in filtered_members(request)
        )
        return csv_response(export_filename("miembros"), header, rows)


member_export = MemberExportView.as_view()


class MemberDetailView(ManageMembersRequiredMixin, DetailView):
    """Member detail view with tabs."""

    model = Member
    template_name = "members/detail.html"
    context_object_name = "member"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()
        return Member.objects.filter(tenant=tenant)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.object

        # Giving history is finance data; the pastoral notes sit behind their own
        # role (the template checks it).
        if self.request.user.can_manage_finance:
            context["donations"] = member.donations.all()[:10]

        return context


member_detail = MemberDetailView.as_view()


class SelectedTagsContextMixin:
    """Expose the ids of the ticked tags as strings, so the hand-written form
    keeps its checkboxes after a failed POST as well as when editing."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["selected_tag_ids"] = [
            str(pk) for pk in (form["tags"].value() or [])
        ]
        return context


class MemberCreateView(
    SelectedTagsContextMixin, ManageMembersRequiredMixin, CreateView
):
    """Create a new member."""

    model = Member
    template_name = "members/form.html"
    fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "date_of_birth",
        "gender",
        "marital_status",
        "is_baptized",
        "baptism_date",
        "member_status",
        "membership_date",
        "family",
        "address",
        "city",
        "state",
        "postal_code",
        "photo",
        "notes",
        "tags",
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["family"].queryset = Family.objects.filter(tenant=tenant)
            form.fields["tags"].queryset = Tag.objects.filter(tenant=tenant)
        if not self.request.user.can_view_pastoral_notes:
            # Whoever can't read the notes can't overwrite them either.
            form.fields.pop("notes")
        return form

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("member_detail", kwargs={"pk": self.object.pk})


member_create = MemberCreateView.as_view()


class MemberUpdateView(
    SelectedTagsContextMixin, ManageMembersRequiredMixin, UpdateView
):
    """Update an existing member."""

    model = Member
    template_name = "members/form.html"
    fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "date_of_birth",
        "gender",
        "marital_status",
        "is_baptized",
        "baptism_date",
        "member_status",
        "membership_date",
        "family",
        "address",
        "city",
        "state",
        "postal_code",
        "photo",
        "notes",
        "tags",
    ]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()
        return Member.objects.filter(tenant=tenant)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["family"].queryset = Family.objects.filter(tenant=tenant)
            form.fields["tags"].queryset = Tag.objects.filter(tenant=tenant)
        if not self.request.user.can_view_pastoral_notes:
            # Whoever can't read the notes can't overwrite them either.
            form.fields.pop("notes")
        return form

    def get_success_url(self):
        return reverse("member_detail", kwargs={"pk": self.object.pk})


member_update = MemberUpdateView.as_view()


class MemberDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete a member."""

    model = Member
    template_name = "members/confirm_delete.html"
    context_object_name = "member"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()
        return Member.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("member_list")


member_delete = MemberDeleteView.as_view()


# ============================================================
# FAMILY VIEWS
# ============================================================


class FamilyListView(ManageMembersRequiredMixin, ListView):
    """List all families."""

    model = Family
    template_name = "families/list.html"
    context_object_name = "families"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return (
            Family.objects.filter(tenant=tenant)
            .select_related("head_of_family")
            .prefetch_related("members")
        )


family_list = FamilyListView.as_view()


class FamilyDetailView(ManageMembersRequiredMixin, DetailView):
    """A family and the people who make it up."""

    model = Family
    template_name = "families/detail.html"
    context_object_name = "family"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant).select_related("head_of_family")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        family = self.object
        people = list(family.members.order_by("last_name", "first_name"))
        # The head first, then everyone else alphabetically.
        people.sort(key=lambda m: m.pk != family.head_of_family_id)
        context["family_members"] = people
        return context


family_detail = FamilyDetailView.as_view()


class FamilyFormMixin:
    """Shared by create/update: the form with the member picker, scoped to
    the user's church."""

    model = Family
    form_class = FamilyForm
    template_name = "families/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = getattr(self.request.user, "tenant", None)
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.request.user.can_view_pastoral_notes:
            form.fields.pop("notes", None)
        return form

    def get_success_url(self):
        return reverse("family_detail", kwargs={"pk": self.object.pk})


class FamilyCreateView(FamilyFormMixin, ManageMembersRequiredMixin, CreateView):
    """Create a new family."""

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Familia \"{self.object.name}\" creada.")
        return response


family_create = FamilyCreateView.as_view()


class FamilyUpdateView(FamilyFormMixin, ManageMembersRequiredMixin, UpdateView):
    """Update an existing family and its members."""

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Familia actualizada.")
        return response


family_update = FamilyUpdateView.as_view()


class FamilyDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete a family."""

    model = Family
    template_name = "families/confirm_delete.html"
    context_object_name = "family"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("family_list")


family_delete = FamilyDeleteView.as_view()


# ============================================================
# TAG VIEWS
# ============================================================


class TagListView(ManageMembersRequiredMixin, ListView):
    """List all tags."""

    model = Tag
    template_name = "tags/list.html"
    context_object_name = "tags"
    paginate_by = 50

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Tag.objects.none()
        return Tag.objects.filter(tenant=tenant).prefetch_related("members")


tag_list = TagListView.as_view()


class TagCreateView(ManageMembersRequiredMixin, CreateView):
    """Create a new tag."""

    model = Tag
    template_name = "tags/form.html"
    fields = ["name", "color"]

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tag_list")


tag_create = TagCreateView.as_view()


class TagUpdateView(ManageMembersRequiredMixin, UpdateView):
    """Update an existing tag."""

    model = Tag
    template_name = "tags/form.html"
    fields = ["name", "color"]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Tag.objects.none()
        return Tag.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("tag_list")


tag_update = TagUpdateView.as_view()


class TagDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete a tag."""

    model = Tag
    template_name = "tags/confirm_delete.html"
    context_object_name = "tag"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Tag.objects.none()
        return Tag.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("tag_list")


tag_delete = TagDeleteView.as_view()


# ============================================================
# MEMBER'S OWN RECORD ("Mi ficha")
# ============================================================


class MyRecordMixin(LoginRequiredMixin):
    """Resolve the record linked to the logged-in user (never another one)."""

    def get_member(self):
        user = self.request.user
        member = user.member_profile
        if member is None or member.tenant_id != user.tenant_id or member.is_deleted:
            return None
        return member


class MyRecordView(MyRecordMixin, TemplateView):
    """The user's own record: their data, courses, certificates, events and
    giving. Open to every role; it only ever shows the linked member."""

    template_name = "members/my_record.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_member()
        context["member"] = member
        if member is None:
            return context
        context["enrollments"] = (
            member.enrollments.exclude(status="dropped")
            .select_related("course", "course__course_block")
            .order_by("-enrolled_at")
        )
        context["certificates"] = member.block_certificates.select_related(
            "course_block"
        ).order_by("-issued_at")
        context["registrations"] = (
            member.event_registrations.filter(
                status="registered", event__start_at__gte=timezone.now()
            )
            .select_related("event")
            .order_by("event__start_at")
        )
        context["donations"] = member.donations.filter(status="completed").order_by(
            "-donation_date"
        )[:20]
        return context


my_record = MyRecordView.as_view()


class MyRecordUpdateView(MyRecordMixin, UpdateView):
    """Let members keep their own contact details up to date."""

    form_class = MyContactForm
    template_name = "members/my_record_form.html"
    success_url = reverse_lazy("my_record")

    def get_object(self, queryset=None):
        member = self.get_member()
        if member is None:
            raise Http404("Tu usuario no está vinculado a una ficha de miembro.")
        return member

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Tus datos de contacto se actualizaron.")
        return response


my_record_update = MyRecordUpdateView.as_view()


# ============================================================
# MEMBER LOOKUP (type-ahead for pickers)
# ============================================================


class MemberLookupView(LoginRequiredMixin, View):
    """JSON search used by the "pick a person" boxes (register for an event,
    enrol in a course, choose a family's members), so those pages don't ship the
    whole directory in their HTML. Names only (plus e-mail and family), and
    only for roles that already see people's names in their daily work."""

    LIMIT = 15
    MAX_LIMIT = 30

    @staticmethod
    def _uuid(value):
        try:
            return uuid.UUID(value) if value else None
        except ValueError:
            return None

    def get(self, request):
        user = request.user
        tenant = getattr(user, "tenant", None)
        if tenant is None or not (
            user.can_manage_members or user.can_manage_education or user.can_manage_finance
        ):
            return JsonResponse({"results": [], "total": 0}, status=403)

        people = search_members(Member.objects.filter(tenant=tenant), request.GET.get("q", ""))

        from education.models import Enrollment
        from events.models import EventRegistration

        # Hide people who are already in the event/course being edited. A bad id
        # just means "exclude nobody".
        event_id = self._uuid(request.GET.get("exclude_event"))
        if event_id:
            people = people.exclude(
                id__in=EventRegistration.objects.filter(
                    event_id=event_id, tenant=tenant, status="registered"
                ).values("member_id")
            )
        course_id = self._uuid(request.GET.get("exclude_course"))
        if course_id:
            people = people.exclude(
                id__in=Enrollment.objects.filter(
                    course_id=course_id, tenant=tenant, status__in=["enrolled", "completed"]
                ).values("member_id")
            )

        try:
            limit = min(max(int(request.GET.get("limit", self.LIMIT)), 1), self.MAX_LIMIT)
        except ValueError:
            limit = self.LIMIT
        total = people.count()
        rows = people.select_related("family").order_by("last_name", "first_name")[:limit]
        return JsonResponse(
            {
                "total": total,
                "results": [
                    {
                        "id": str(person.pk),
                        "name": person.full_name,
                        "email": person.email or "",
                        "family": person.family.name if person.family else "",
                        "family_id": str(person.family_id) if person.family_id else "",
                    }
                    for person in rows
                ],
            }
        )


member_lookup = MemberLookupView.as_view()
