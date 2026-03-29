"""
Member, Family, and Tag views.
"""

from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.db import models
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from .models import Member, Family, Tag
from tenants.models import Tenant
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
        return render(request, self.template_name)

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
        return render(request, self.template_name)

    def post(self, request):
        if "onboarding_church" not in request.session:
            return redirect("onboarding_church")
        if "onboarding_admin" not in request.session:
            return redirect("onboarding_admin")

        # Store settings in session
        request.session["onboarding_settings"] = {
            "currency": request.POST.get("currency", "USD"),
            "timezone": request.POST.get("timezone", "America/New_York"),
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


class MemberListView(LoginRequiredMixin, ListView):
    """List all members with filtering and search."""

    model = Member
    template_name = "members/list.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()

        queryset = Member.objects.filter(tenant=tenant)

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(member_status=status)

        # Filter by family
        family_id = self.request.GET.get("family")
        if family_id:
            queryset = queryset.filter(family_id=family_id)

        # Filter by tag
        tag_id = self.request.GET.get("tag")
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)

        # Search
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(phone__icontains=search)
            )

        return (
            queryset.select_related("family")
            .prefetch_related("tags")
            .order_by("last_name", "first_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if tenant:
            context["families"] = Family.objects.filter(tenant=tenant)
            context["tags"] = Tag.objects.filter(tenant=tenant)

        return context


member_list = MemberListView.as_view()


class MemberDetailView(LoginRequiredMixin, DetailView):
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

        # Get donations for this member
        context["donations"] = member.donations.all()[:10]

        return context


member_detail = MemberDetailView.as_view()


class MemberCreateView(LoginRequiredMixin, CreateView):
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
        return form

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("member_detail", kwargs={"pk": self.object.pk})


member_create = MemberCreateView.as_view()


class MemberUpdateView(LoginRequiredMixin, UpdateView):
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
        return form

    def get_success_url(self):
        return reverse("member_detail", kwargs={"pk": self.object.pk})


member_update = MemberUpdateView.as_view()


class MemberDeleteView(LoginRequiredMixin, DeleteView):
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


class FamilyListView(LoginRequiredMixin, ListView):
    """List all families."""

    model = Family
    template_name = "families/list.html"
    context_object_name = "families"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant).prefetch_related("members")


family_list = FamilyListView.as_view()


class FamilyCreateView(LoginRequiredMixin, CreateView):
    """Create a new family."""

    model = Family
    template_name = "families/form.html"
    fields = [
        "name",
        "head_of_family",
        "address",
        "city",
        "state",
        "postal_code",
        "home_phone",
        "notes",
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["head_of_family"].queryset = Member.objects.filter(
                tenant=tenant
            )
        return form

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("family_list")


family_create = FamilyCreateView.as_view()


class FamilyUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing family."""

    model = Family
    template_name = "families/form.html"
    fields = [
        "name",
        "head_of_family",
        "address",
        "city",
        "state",
        "postal_code",
        "home_phone",
        "notes",
    ]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["head_of_family"].queryset = Member.objects.filter(
                tenant=tenant
            )
        return form

    def get_success_url(self):
        return reverse("family_list")


family_update = FamilyUpdateView.as_view()


class FamilyDeleteView(LoginRequiredMixin, DeleteView):
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


class TagListView(LoginRequiredMixin, ListView):
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


class TagCreateView(LoginRequiredMixin, CreateView):
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


class TagUpdateView(LoginRequiredMixin, UpdateView):
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


class TagDeleteView(LoginRequiredMixin, DeleteView):
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
