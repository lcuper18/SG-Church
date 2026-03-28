"""
URL configuration for Finance API.
"""

from rest_framework.routers import DefaultRouter
from .views import DonationViewSet, ExpenseViewSet, CampaignViewSet

app_name = "finance_api"

router = DefaultRouter()
router.register(r"donations", DonationViewSet, basename="donation")
router.register(r"expenses", ExpenseViewSet, basename="expense")
router.register(r"campaigns", CampaignViewSet, basename="campaign")

urlpatterns = router.urls
