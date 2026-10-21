"""Family views."""

from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import ManageMembersRequiredMixin

from ..forms import FamilyForm
from ..models import Family


class FamilyListView(ManageMembersRequiredMixin, ListView):
    """List all families."""

    model = Family
    template_name = "families/list.html"
    context_object_name = "families"
    paginate_by = 25

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return (
            Family.objects.filter(tenant=tenant)
            .select_related("head_of_family")
            .prefetch_related("members")
        )


family_list = FamilyListView.as_view()


class FamilyDetailView(ManageMembersRequiredMixin, DetailView):
    """A family and the people who make it up."""

    model = Family
    template_name = "families/detail.html"
    context_object_name = "family"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant).select_related("head_of_family")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        family = self.object
        people = list(family.members.order_by("last_name", "first_name"))
        # The head first, then everyone else alphabetically.
        people.sort(key=lambda m: m.pk != family.head_of_family_id)
        context["family_members"] = people
        return context


family_detail = FamilyDetailView.as_view()


class FamilyFormMixin:
    """Shared by create/update: the form with the member picker, scoped to
    the user's church."""

    model = Family
    form_class = FamilyForm
    template_name = "families/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = getattr(self.request.user, "tenant", None)
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.request.user.can_view_pastoral_notes:
            form.fields.pop("notes", None)
        return form

    def get_success_url(self):
        return reverse("family_detail", kwargs={"pk": self.object.pk})


class FamilyCreateView(FamilyFormMixin, ManageMembersRequiredMixin, CreateView):
    """Create a new family."""

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Familia \"{self.object.name}\" creada.")
        return response


family_create = FamilyCreateView.as_view()


class FamilyUpdateView(FamilyFormMixin, ManageMembersRequiredMixin, UpdateView):
    """Update an existing family and its members."""

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Familia actualizada.")
        return response


family_update = FamilyUpdateView.as_view()


class FamilyDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete a family."""

    model = Family
    template_name = "families/confirm_delete.html"
    context_object_name = "family"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Family.objects.none()
        return Family.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("family_list")


family_delete = FamilyDeleteView.as_view()
