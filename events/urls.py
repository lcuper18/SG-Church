# Events URLs
from django.urls import path
from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("create/", views.event_create, name="event_create"),
    path("attendance/report/", views.attendance_report, name="attendance_report"),
    path("<uuid:pk>/", views.event_detail, name="event_detail"),
    path("<uuid:pk>/attendance/", views.event_attendance, name="event_attendance"),
    path("<uuid:pk>/edit/", views.event_update, name="event_update"),
    path("<uuid:pk>/delete/", views.event_delete, name="event_delete"),
    path("<uuid:event_pk>/register/", views.registration_create, name="registration_create"),
    path("registrations/<uuid:pk>/cancel/", views.registration_cancel, name="registration_cancel"),
]
