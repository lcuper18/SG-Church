# Core URLs
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from members import views as members_views

urlpatterns = [
    # Home and Dashboard
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Onboarding
    path(
        "onboarding/",
        members_views.OnboardingStartView.as_view(),
        name="onboarding_start",
    ),
    path(
        "onboarding/church/",
        members_views.OnboardingChurchView.as_view(),
        name="onboarding_church",
    ),
    path(
        "onboarding/admin/",
        members_views.OnboardingAdminView.as_view(),
        name="onboarding_admin",
    ),
    path(
        "onboarding/settings/",
        members_views.OnboardingSettingsView.as_view(),
        name="onboarding_settings",
    ),
    path(
        "onboarding/complete/",
        members_views.OnboardingCompleteView.as_view(),
        name="onboarding_complete_setup",
    ),
]
