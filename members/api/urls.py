"""
URL configuration for Members API.
"""

from rest_framework.routers import DefaultRouter
from .views import MemberViewSet, FamilyViewSet, TagViewSet

app_name = "members_api"

router = DefaultRouter()
router.register(r"members", MemberViewSet, basename="member")
router.register(r"families", FamilyViewSet, basename="family")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = router.urls
