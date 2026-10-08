# Core URLs
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from members import views as members_views

urlpatterns = [
    # Home and Dashboard
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # Profile and church settings
    path("profile/", views.profile, name="profile"),
    path("settings/", views.ChurchSettingsView.as_view(), name="church_settings"),
    # User management (church administrators)
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/create/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<uuid:pk>/edit/", views.UserUpdateView.as_view(), name="user_update"),
    path(
        "users/<uuid:pk>/toggle-active/",
        views.UserToggleActiveView.as_view(),
        name="user_toggle_active",
    ),
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
