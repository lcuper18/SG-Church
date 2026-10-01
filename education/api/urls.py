"""
URL configuration for Education (courses) API.
"""

from rest_framework.routers import DefaultRouter

from .views import (
    BlockCertificateViewSet,
    CourseBlockViewSet,
    CourseViewSet,
    EnrollmentViewSet,
)

app_name = "education_api"

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"course-blocks", CourseBlockViewSet, basename="course-block")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")
router.register(r"certificates", BlockCertificateViewSet, basename="block-certificate")

urlpatterns = router.urls
