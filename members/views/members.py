"""Member list, detail, create, update, delete and export."""

import uuid

from django.db import models
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from core.exports import csv_response, export_filename
from core.mixins import ManageMembersRequiredMixin
from tenants.models import Site

from ..models import Family, Member, Tag
from ..search import search_members


def _limit_site_field(form, tenant):
    """The "home site" picker: this church's active sites, or gone entirely when
    the church has only one."""
    if not tenant.uses_sites:
        del form.fields["home_site"]
        return
    current = form.instance.home_site_id
    form.fields["home_site"].queryset = Site.objects.filter(tenant=tenant).filter(
        models.Q(is_active=True) | models.Q(pk=current)
    )
    form.fields["home_site"].required = False


def filtered_members(request):
    """The tenant's members narrowed by the list page's query-string filters
    (shared by the list and its CSV export)."""
    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        return Member.objects.none()

    queryset = Member.objects.filter(tenant=tenant)

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(member_status=status)

    family_id = request.GET.get("family")
    if family_id:
        queryset = queryset.filter(family_id=family_id)

    site_id = request.GET.get("site")
    if site_id:
        try:
            queryset = queryset.filter(home_site_id=uuid.UUID(site_id))
        except ValueError:
            queryset = queryset.none()

    tag_id = request.GET.get("tag")
    if tag_id:
        queryset = queryset.filter(tags__id=tag_id)

    search = request.GET.get("search")
    if search:
        queryset = search_members(queryset, search)

    return (
        queryset.select_related("family", "home_site")
        .prefetch_related("tags")
        .order_by("last_name", "first_name")
    )


class MemberListView(ManageMembersRequiredMixin, ListView):
    """List all members with filtering and search."""

    model = Member
    template_name = "members/list.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        return filtered_members(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, "tenant", None)

        if tenant:
            context["families"] = Family.objects.filter(tenant=tenant)
            if tenant.uses_sites:
                context["site_choices"] = Site.objects.filter(tenant=tenant)
            context["tags"] = Tag.objects.filter(tenant=tenant)

        return context


member_list = MemberListView.as_view()


class MemberExportView(ManageMembersRequiredMixin, View):
    """Download the members matching the list's current filters. Restricted to
    roles that manage members: the file carries phones, addresses and birth
    dates for the whole directory."""

    def get(self, request):
        header = [
            "Nombre", "Apellido", "Email", "Teléfono", "Identificación", "Fecha de nacimiento", "Género",
            "Estado civil", "Bautizado", "Fecha de bautismo", "Estado", "Fecha de membresía",
            "Familia", "Dirección", "Ciudad", "Estado/Provincia", "Código postal", "Etiquetas", "Sede",
        ]
        rows = (
            [
                m.first_name, m.last_name, m.email, m.phone, m.national_id, m.date_of_birth,
                m.get_gender_display(), m.get_marital_status_display(), m.is_baptized,
                m.baptism_date, m.get_member_status_display(), m.membership_date,
                m.family.name if m.family else "", m.address, m.city, m.state,
                m.postal_code, ", ".join(t.name for t in m.tags.all()), m.home_site.name if m.home_site else "",
            ]
            for m in filtered_members(request)
        )
        return csv_response(export_filename("miembros"), header, rows)


member_export = MemberExportView.as_view()


class MemberDetailView(ManageMembersRequiredMixin, DetailView):
    """Member detail view with tabs."""

    model = Member
    template_name = "members/detail.html"
    context_object_name = "member"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()
        return Member.objects.filter(tenant=tenant)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.object

        # Giving history is finance data; the pastoral notes sit behind their own
        # role (the template checks it).
        if self.request.user.can_manage_finance:
            context["donations"] = member.donations.all()[:10]
        if self.request.user.can_view_pastoral_notes:
            from ..forms import FollowUpForm

            context["follow_ups"] = member.follow_ups.select_related("assigned_to")
            context["follow_up_form"] = FollowUpForm(tenant=self.request.user.tenant)

        return context


member_detail = MemberDetailView.as_view()


class SelectedTagsContextMixin:
    """Expose the ids of the ticked tags as strings, so the hand-written form
    keeps its checkboxes after a failed POST as well as when editing."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["selected_tag_ids"] = [
            str(pk) for pk in (form["tags"].value() or [])
        ]
        return context


class MemberCreateView(
    SelectedTagsContextMixin, ManageMembersRequiredMixin, CreateView
):
    """Create a new member."""

    model = Member
    template_name = "members/form.html"
    fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "national_id",
        "date_of_birth",
        "gender",
        "marital_status",
        "is_baptized",
        "baptism_date",
        "member_status",
        "membership_date",
        "family",
        "home_site",
        "address",
        "city",
        "state",
        "postal_code",
        "photo",
        "notes",
        "tags",
        "email_opt_out",
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant  # lets Member.clean() check the ID is unique here
            form.fields["family"].queryset = Family.objects.filter(tenant=tenant)
            form.fields["tags"].queryset = Tag.objects.filter(tenant=tenant)
            _limit_site_field(form, tenant)
        if not self.request.user.can_view_pastoral_notes:
            # Whoever can't read the notes can't overwrite them either.
            form.fields.pop("notes")
        return form

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("member_detail", kwargs={"pk": self.object.pk})


member_create = MemberCreateView.as_view()


class MemberUpdateView(
    SelectedTagsContextMixin, ManageMembersRequiredMixin, UpdateView
):
    """Update an existing member."""

    model = Member
    template_name = "members/form.html"
    fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "national_id",
        "date_of_birth",
        "gender",
        "marital_status",
        "is_baptized",
        "baptism_date",
        "member_status",
        "membership_date",
        "family",
        "home_site",
        "address",
        "city",
        "state",
        "postal_code",
        "photo",
        "notes",
        "tags",
        "email_opt_out",
    ]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()
        return Member.objects.filter(tenant=tenant)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["family"].queryset = Family.objects.filter(tenant=tenant)
            form.fields["tags"].queryset = Tag.objects.filter(tenant=tenant)
            _limit_site_field(form, tenant)
        if not self.request.user.can_view_pastoral_notes:
            # Whoever can't read the notes can't overwrite them either.
            form.fields.pop("notes")
        return form

    def get_success_url(self):
        return reverse("member_detail", kwargs={"pk": self.object.pk})


member_update = MemberUpdateView.as_view()


class MemberDeleteView(ManageMembersRequiredMixin, DeleteView):
    """Delete a member."""

    model = Member
    template_name = "members/confirm_delete.html"
    context_object_name = "member"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Member.objects.none()
        return Member.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("member_list")


member_delete = MemberDeleteView.as_view()
