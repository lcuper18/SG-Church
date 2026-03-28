"""
Member views.
"""

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from .models import Member


class MemberListView(LoginRequiredMixin, ListView):
    model = Member
    template_name = "members/list.html"
    context_object_name = "members"
    paginate_by = 50

    def get_queryset(self):
        queryset = Member.objects.all()

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(member_status=status)

        # Search
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
            )

        return queryset.order_by("last_name", "first_name")


member_list = MemberListView.as_view()
