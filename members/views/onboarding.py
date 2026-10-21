"""Onboarding wizard for a new church."""

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, View

from members.models import User
from tenants.models import Tenant
from tenants.timezones import DEFAULT_TIMEZONE, TIMEZONE_CHOICES, defaults_for_country, get_zone


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
