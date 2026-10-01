# Education (courses) URLs
from django.urls import path
from . import views

urlpatterns = [
    # Courses
    path("", views.course_list, name="course_list"),
    path("create/", views.course_create, name="course_create"),
    path("<uuid:pk>/", views.course_detail, name="course_detail"),
    path("<uuid:pk>/edit/", views.course_update, name="course_update"),
    path("<uuid:pk>/delete/", views.course_delete, name="course_delete"),
    # Course blocks
    path("blocks/", views.course_block_list, name="course_block_list"),
    path("blocks/create/", views.course_block_create, name="course_block_create"),
    path("blocks/<uuid:pk>/", views.course_block_detail, name="course_block_detail"),
    path(
        "blocks/<uuid:pk>/edit/",
        views.course_block_update,
        name="course_block_update",
    ),
    path(
        "blocks/<uuid:pk>/delete/",
        views.course_block_delete,
        name="course_block_delete",
    ),
    # Enrollment actions
    path("<uuid:course_pk>/enroll/", views.enrollment_create, name="enrollment_create"),
    path(
        "enrollments/<uuid:pk>/complete/",
        views.enrollment_complete,
        name="enrollment_complete",
    ),
    path(
        "enrollments/<uuid:pk>/drop/", views.enrollment_delete, name="enrollment_delete"
    ),
    # Certificates
    path(
        "certificates/<uuid:pk>/",
        views.block_certificate_detail,
        name="block_certificate_detail",
    ),
]
