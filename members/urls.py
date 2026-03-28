# Members URLs
from django.urls import path
from . import views

urlpatterns = [
    # Members
    path("", views.member_list, name="member_list"),
    path("create/", views.member_create, name="member_create"),
    path("<uuid:pk>/", views.member_detail, name="member_detail"),
    path("<uuid:pk>/edit/", views.member_update, name="member_update"),
    path("<uuid:pk>/delete/", views.member_delete, name="member_delete"),
    # Families
    path("families/", views.family_list, name="family_list"),
    path("families/create/", views.family_create, name="family_create"),
    path("families/<uuid:pk>/edit/", views.family_update, name="family_update"),
    path("families/<uuid:pk>/delete/", views.family_delete, name="family_delete"),
    # Tags
    path("tags/", views.tag_list, name="tag_list"),
    path("tags/create/", views.tag_create, name="tag_create"),
    path("tags/<uuid:pk>/edit/", views.tag_update, name="tag_update"),
    path("tags/<uuid:pk>/delete/", views.tag_delete, name="tag_delete"),
]
