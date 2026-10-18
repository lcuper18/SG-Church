# Members URLs
from django.urls import path
from . import followups, views

urlpatterns = [
    # Members
    path("", views.member_list, name="member_list"),
    path("create/", views.member_create, name="member_create"),
    path("export/", views.member_export, name="member_export"),
    path("lookup/", views.member_lookup, name="member_lookup"),
    path("import/", views.member_import, name="member_import"),
    path("import/confirm/", views.member_import_confirm, name="member_import_confirm"),
    path("import/template/", views.member_import_template, name="member_import_template"),
    path("followups/", followups.follow_up_list, name="follow_up_list"),
    path("followups/<uuid:pk>/edit/", followups.follow_up_edit, name="follow_up_edit"),
    path("followups/<uuid:pk>/done/", followups.follow_up_done, name="follow_up_done"),
    path("followups/<uuid:pk>/reopen/", followups.follow_up_reopen, name="follow_up_reopen"),
    path("followups/<uuid:pk>/delete/", followups.follow_up_delete, name="follow_up_delete"),
    path("<uuid:pk>/followups/add/", followups.follow_up_add, name="follow_up_add"),
    path("<uuid:pk>/", views.member_detail, name="member_detail"),
    path("<uuid:pk>/edit/", views.member_update, name="member_update"),
    path("<uuid:pk>/delete/", views.member_delete, name="member_delete"),
    # Families
    path("families/", views.family_list, name="family_list"),
    path("families/create/", views.family_create, name="family_create"),
    path("families/<uuid:pk>/", views.family_detail, name="family_detail"),
    path("families/<uuid:pk>/edit/", views.family_update, name="family_update"),
    path("families/<uuid:pk>/delete/", views.family_delete, name="family_delete"),
    # Tags
    path("tags/", views.tag_list, name="tag_list"),
    path("tags/create/", views.tag_create, name="tag_create"),
    path("tags/<uuid:pk>/edit/", views.tag_update, name="tag_update"),
    path("tags/<uuid:pk>/delete/", views.tag_delete, name="tag_delete"),
]
