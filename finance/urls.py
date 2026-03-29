# Finance URLs
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("", views.finance_dashboard, name="finance_dashboard"),
    # Donations
    path("donations/", views.donation_list, name="donation_list"),
    path("donations/<uuid:pk>/", views.donation_detail, name="donation_detail"),
    # Expenses
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/create/", views.expense_create, name="expense_create"),
    path("expenses/<uuid:pk>/edit/", views.expense_update, name="expense_update"),
    path("expenses/<uuid:pk>/delete/", views.expense_delete, name="expense_delete"),
    # Reports
    path("reports/income-statement/", views.income_statement, name="income_statement"),
    path(
        "reports/donations-by-member/",
        views.donations_by_member,
        name="donations_by_member",
    ),
]
