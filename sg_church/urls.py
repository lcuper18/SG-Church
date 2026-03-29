"""
URL configuration for SG Church project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
import allauth.urls
from allauth.account.views import LoginView, LogoutView, SignupView, PasswordResetView


# Simple health check endpoint
def health_check(request):
    return HttpResponse("OK")


# Override allauth URLs to use custom templates
# Using simple include without namespace to avoid conflicts
allauth_url_patterns = [
    path(
        "login/",
        LoginView.as_view(template_name="account/login.html"),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(template_name="account/logout.html"),
        name="logout",
    ),
    path(
        "signup/",
        SignupView.as_view(template_name="account/signup.html"),
        name="signup",
    ),
    path(
        "password/reset/",
        PasswordResetView.as_view(),
        name="password_reset",
    ),
]

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health check
    path("health/", health_check, name="health_check"),
    # Allauth (authentication) - custom templates
    path("accounts/", include(allauth_url_patterns)),
    path("accounts/social/", include("allauth.socialaccount.urls")),
    # Local apps
    path("api/v1/", include("members.api.urls")),
    path("api/v1/", include("finance.api.urls")),
    path("api/v1/", include("notifications.urls")),
    # Public donation pages
    path(
        "donate/",
        lambda r: __import__("finance.views", fromlist=["donate_page"]).donate_page(r),
        name="donate_page",
    ),
    path(
        "donate/checkout/",
        lambda r: __import__(
            "finance.views", fromlist=["create_checkout_session"]
        ).create_checkout_session(r),
        name="donate_checkout",
    ),
    path(
        "donate/success/",
        lambda r: __import__(
            "finance.views", fromlist=["donation_success"]
        ).donation_success(r),
        name="donate_success",
    ),
    path(
        "api/v1/webhooks/stripe/",
        lambda r: __import__(
            "finance.views", fromlist=["stripe_webhook"]
        ).stripe_webhook(r),
        name="stripe_webhook",
    ),
    # Home and members
    path("", include("core.urls")),
    path("members/", include("members.urls")),
    path("finance/", include("finance.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
