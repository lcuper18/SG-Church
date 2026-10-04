"""
URL configuration for Events API.
"""

from rest_framework.routers import DefaultRouter

from .views import EventAttendanceViewSet, EventRegistrationViewSet, EventViewSet

app_name = "events_api"

router = DefaultRouter()
router.register(r"events", EventViewSet, basename="event")
router.register(r"event-registrations", EventRegistrationViewSet, basename="event-registration")
router.register(r"event-attendances", EventAttendanceViewSet, basename="event-attendance")

urlpatterns = router.urls
