"""
URL configuration for Members API.
"""

from rest_framework.routers import DefaultRouter
from .views import MemberViewSet, FamilyViewSet

app_name = "members_api"

router = DefaultRouter()
router.register(r"members", MemberViewSet, basename="member")
router.register(r"families", FamilyViewSet, basename="family")

urlpatterns = router.urls
