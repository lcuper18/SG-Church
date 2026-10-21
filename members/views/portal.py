"""Mi ficha: what a member sees and edits about their own record."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView

from ..forms import MyContactForm


class MyRecordMixin(LoginRequiredMixin):
    """Resolve the record linked to the logged-in user (never another one)."""

    def get_member(self):
        user = self.request.user
        member = user.member_profile
        if member is None or member.tenant_id != user.tenant_id or member.is_deleted:
            return None
        return member


class MyRecordView(MyRecordMixin, TemplateView):
    """The user's own record: their data, courses, certificates, events and
    giving. Open to every role; it only ever shows the linked member."""

    template_name = "members/my_record.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_member()
        context["member"] = member
        if member is None:
            return context
        context["enrollments"] = (
            member.enrollments.exclude(status="dropped")
            .select_related("course", "course__course_block")
            .order_by("-enrolled_at")
        )
        context["certificates"] = member.block_certificates.select_related(
            "course_block"
        ).order_by("-issued_at")
        context["registrations"] = (
            member.event_registrations.filter(
                status="registered", event__start_at__gte=timezone.now()
            )
            .select_related("event", "event__site")
            .order_by("event__start_at")
        )
        context["donations"] = member.donations.filter(status="completed").order_by(
            "-donation_date"
        )[:20]
        return context


my_record = MyRecordView.as_view()


class MyRecordUpdateView(MyRecordMixin, UpdateView):
    """Let members keep their own contact details up to date."""

    form_class = MyContactForm
    template_name = "members/my_record_form.html"
    success_url = reverse_lazy("my_record")

    def get_object(self, queryset=None):
        member = self.get_member()
        if member is None:
            raise Http404("Tu usuario no está vinculado a una ficha de miembro.")
        return member

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Tus datos de contacto se actualizaron.")
        return response


my_record_update = MyRecordUpdateView.as_view()
