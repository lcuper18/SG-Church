"""
Core views for SG Church.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def home(request):
    """Home page."""
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    """Dashboard for logged-in users."""
    return render(request, "core/dashboard.html")
