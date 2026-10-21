"""Tag views."""

from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import ManageMembersRequiredMixin

from ..models import Tag


class TagListView(ManageMembersRequiredMixin, ListView):
    """List all tags."""

    model = Tag
    template_name = "tags/list.html"
    context_object_name = "tags"
    paginate_by = 50

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Tag.objects.none()
        return Tag.objects.filter(tenant=tenant).prefetch_related("members")


tag_list = TagListView.as_view()


class TagCreateView(ManageMembersRequiredMixin, CreateView):
    """Create a new tag."""

    model = Tag
    template_name = "tags/form.html"
    fields = ["name", "color"]

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tag_list")


tag_create = TagCreateView.as_view()


class TagUpdateView(ManageMembersRequiredMixin, UpdateView):
    """Update an existing tag."""

    model = Tag
    template_name = "tags/form.html"
    fields = ["name", "color"]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Tag.objects.none()
        return Tag.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("tag_list")


tag_update = TagUpdateView.as_view()


class TagDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete a tag."""

    model = Tag
    template_name = "tags/confirm_delete.html"
    context_object_name = "tag"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Tag.objects.none()
        return Tag.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("tag_list")


tag_delete = TagDeleteView.as_view()
