"""
URL configuration for SG Church project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Allauth (authentication)
    path("accounts/", include("allauth.urls")),
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
