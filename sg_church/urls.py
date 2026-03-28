"""
URL configuration for SG Church project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import allauth.urls

# Override allauth URLs to use custom templates
# Remove default allauth and add our custom versions
allauth_url_patterns = [
    path(
        "login/",
        allauth.urls.LoginView.as_view(template_name="account/login.html"),
        name="account_login",
    ),
    path(
        "logout/",
        allauth.urls.LogoutView.as_view(template_name="account/logout.html"),
        name="account_logout",
    ),
    path(
        "signup/",
        allauth.urls.SignupView.as_view(template_name="account/signup.html"),
        name="account_signup",
    ),
    path(
        "password/reset/",
        allauth.urls.PasswordResetView.as_view(),
        name="account_reset_password",
    ),
]

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Allauth (authentication) - custom templates
    path("accounts/", include((allauth_url_patterns, "allauth"), namespace="account")),
    path("accounts/social/", include("allauth.socialaccount.urls")),
    # Local apps
    path("api/v1/", include("members.api.urls")),
    path("api/v1/", include("finance.api.urls")),
    # Home and members
    path("", include("core.urls")),
    path("members/", include("members.urls")),
    path("finance/", include("finance.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
