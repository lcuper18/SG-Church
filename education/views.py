"""
Course, course block, and enrollment views.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import ManageEducationRequiredMixin, ManageMembersRequiredMixin
from emails import notify
from members.models import Member, User

from .models import BlockCertificate, Course, CourseBlock, Enrollment


def _next_order(block):
    """Position after the block's last course."""
    last = block.courses.aggregate(last=Max("order_in_block"))["last"]
    return 1 if last is None else last + 1


# ============================================================
# COURSE VIEWS
# ============================================================


class CourseListView(LoginRequiredMixin, ListView):
    """List all courses for the tenant."""

    model = Course
    template_name = "education/course_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Course.objects.none()
        return Course.objects.filter(tenant=tenant).select_related("course_block")


course_list = CourseListView.as_view()


class CourseDetailView(LoginRequiredMixin, DetailView):
    """Course detail: requirements, prerequisites, enrolled members."""

    model = Course
    template_name = "education/course_detail.html"
    context_object_name = "course"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Course.objects.none()
        return Course.objects.filter(tenant=tenant)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        if not self.request.user.can_view_roster:
            return context

        context["enrollments"] = course.enrollments.select_related("member").exclude(
            status="dropped"
        )
        return context


course_detail = CourseDetailView.as_view()


class CourseCreateView(ManageEducationRequiredMixin, CreateView):
    """Create a new course."""

    model = Course
    template_name = "education/course_form.html"
    fields = [
        "title",
        "description",
        "instructor",
        "is_active",
        "capacity",
        "requires_baptized",
        "requires_married",
        "prerequisite_courses",
        "course_block",
        "order_in_block",
    ]

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["instructor"].queryset = User.objects.filter(tenant=tenant)
            form.fields["prerequisite_courses"].queryset = Course.objects.filter(
                tenant=tenant
            )
            form.fields["course_block"].queryset = CourseBlock.objects.filter(
                tenant=tenant
            )
        return form

    def _block_from_query(self):
        """The block named by `?block=<uuid>` (the "new course in this block"
        link), only if it belongs to the user's church."""
        tenant = getattr(self.request.user, "tenant", None)
        try:
            return CourseBlock.objects.filter(
                tenant=tenant, pk=self.request.GET.get("block")
            ).first()
        except (ValidationError, ValueError):
            return None

    def get_initial(self):
        initial = super().get_initial()
        block = self._block_from_query()
        if block:
            initial["course_block"] = block.pk
            initial["order_in_block"] = _next_order(block)
        return initial

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        # Coming from a block's page, go back to it.
        block = self._block_from_query()
        if block:
            return reverse("course_block_detail", kwargs={"pk": block.pk})
        return reverse("course_detail", kwargs={"pk": self.object.pk})


course_create = CourseCreateView.as_view()


class CourseUpdateView(ManageEducationRequiredMixin, UpdateView):
    """Update an existing course."""

    model = Course
    template_name = "education/course_form.html"
    fields = [
        "title",
        "description",
        "instructor",
        "is_active",
        "capacity",
        "requires_baptized",
        "requires_married",
        "prerequisite_courses",
        "course_block",
        "order_in_block",
    ]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Course.objects.none()
        return Course.objects.filter(tenant=tenant)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.fields["instructor"].queryset = User.objects.filter(tenant=tenant)
            form.fields["prerequisite_courses"].queryset = Course.objects.filter(
                tenant=tenant
            ).exclude(pk=self.object.pk)
            form.fields["course_block"].queryset = CourseBlock.objects.filter(
                tenant=tenant
            )
        return form

    def get_success_url(self):
        return reverse("course_detail", kwargs={"pk": self.object.pk})


course_update = CourseUpdateView.as_view()


class CourseDeleteView(ManageEducationRequiredMixin, DeleteView):
    """Delete a course."""

    model = Course
    template_name = "education/course_confirm_delete.html"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return Course.objects.none()
        return Course.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("course_list")


course_delete = CourseDeleteView.as_view()


# ============================================================
# COURSE BLOCK VIEWS
# ============================================================


class CourseBlockListView(LoginRequiredMixin, ListView):
    """List all course blocks for the tenant."""

    model = CourseBlock
    template_name = "education/course_block_list.html"
    context_object_name = "course_blocks"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return CourseBlock.objects.none()
        return CourseBlock.objects.filter(tenant=tenant)


course_block_list = CourseBlockListView.as_view()


class CourseBlockDetailView(LoginRequiredMixin, DetailView):
    """Course block detail: courses in the block and per-member progress."""

    model = CourseBlock
    template_name = "education/course_block_detail.html"
    context_object_name = "course_block"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return CourseBlock.objects.none()
        return CourseBlock.objects.filter(tenant=tenant)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        block = self.object
        courses = list(block.courses.filter(is_active=True))
        total = len(courses)
        course_ids = [c.id for c in courses]
        context["courses"] = courses
        if not self.request.user.can_view_roster:
            return context

        # Everyone enrolled in any of the block's courses, with how many they
        # finished: two queries in total, however many people there are.
        enrollments = (
            Enrollment.objects.filter(course_id__in=course_ids)
            .exclude(status="dropped")
            .values_list("member_id", "status")
        )
        completed_by_member = {}
        for member_id, status in enrollments:
            completed_by_member.setdefault(member_id, 0)
            if status == "completed":
                completed_by_member[member_id] += 1

        certificates = {c.member_id: c for c in block.certificates.all()}
        members = Member.objects.filter(id__in=list(completed_by_member))

        progress = [
            {
                "member": member,
                "completed": completed_by_member[member.id],
                "total": total,
                "certificate": certificates.get(member.id),
            }
            for member in members
        ]

        context["courses"] = courses
        context["progress"] = progress
        if self.request.user.can_manage_education:
            context["available_courses"] = Course.objects.filter(
                tenant=block.tenant, course_block__isnull=True, is_active=True
            ).order_by("title")
        return context


course_block_detail = CourseBlockDetailView.as_view()


class BlockAddCourseView(ManageEducationRequiredMixin, View):
    """Put an existing standalone course into a block (POST only), after the
    block's last course."""

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        block = get_object_or_404(CourseBlock, pk=pk, tenant=tenant)
        try:
            course = Course.objects.filter(
                tenant=tenant, pk=request.POST.get("course")
            ).first()
        except (ValidationError, ValueError):
            course = None

        if course is None:
            messages.error(request, "Elige un curso de la lista.")
        elif course.course_block_id is not None:
            messages.error(
                request,
                f"\"{course.title}\" ya pertenece a otro bloque. "
                "Quítalo de ese bloque primero.",
            )
        else:
            course.course_block = block
            course.order_in_block = _next_order(block)
            course.save(update_fields=["course_block", "order_in_block"])
            messages.success(request, f"\"{course.title}\" se agregó al bloque.")
        return redirect("course_block_detail", pk=block.pk)


block_add_course = BlockAddCourseView.as_view()


class BlockRemoveCourseView(ManageEducationRequiredMixin, View):
    """Take a course out of its block, leaving it standalone (POST only)."""

    def post(self, request, pk, course_pk):
        tenant = getattr(request.user, "tenant", None)
        block = get_object_or_404(CourseBlock, pk=pk, tenant=tenant)
        course = get_object_or_404(Course, pk=course_pk, tenant=tenant, course_block=block)
        course.course_block = None
        course.order_in_block = 0
        course.save(update_fields=["course_block", "order_in_block"])
        messages.success(request, f"\"{course.title}\" ya no pertenece al bloque.")
        return redirect("course_block_detail", pk=block.pk)


block_remove_course = BlockRemoveCourseView.as_view()


class CourseBlockCreateView(ManageEducationRequiredMixin, CreateView):
    """Create a new course block."""

    model = CourseBlock
    template_name = "education/course_block_form.html"
    fields = ["name", "description", "is_active"]

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("course_block_detail", kwargs={"pk": self.object.pk})


course_block_create = CourseBlockCreateView.as_view()


class CourseBlockUpdateView(ManageEducationRequiredMixin, UpdateView):
    """Update an existing course block."""

    model = CourseBlock
    template_name = "education/course_block_form.html"
    fields = ["name", "description", "is_active"]

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return CourseBlock.objects.none()
        return CourseBlock.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("course_block_detail", kwargs={"pk": self.object.pk})


course_block_update = CourseBlockUpdateView.as_view()


class CourseBlockDeleteView(ManageEducationRequiredMixin, DeleteView):
    """Delete a course block."""

    model = CourseBlock
    template_name = "education/course_block_confirm_delete.html"

    def get_queryset(self):
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return CourseBlock.objects.none()
        return CourseBlock.objects.filter(tenant=tenant)

    def get_success_url(self):
        return reverse("course_block_list")


course_block_delete = CourseBlockDeleteView.as_view()


# ============================================================
# ENROLLMENT ACTIONS
# ============================================================


class EnrollmentCreateView(ManageMembersRequiredMixin, View):
    """Enroll a member in a course (POST only)."""

    def post(self, request, course_pk):
        tenant = getattr(request.user, "tenant", None)
        course = get_object_or_404(Course, pk=course_pk, tenant=tenant)
        member = get_object_or_404(
            Member, pk=request.POST.get("member"), tenant=tenant
        )

        allowed, reason = course.can_enroll(member)
        if not allowed:
            messages.error(request, reason)
            return redirect("course_detail", pk=course.pk)

        enrollment, created = Enrollment.objects.get_or_create(
            tenant=tenant,
            member=member,
            course=course,
            defaults={"status": "enrolled"},
        )
        if not created and enrollment.status == "dropped":
            enrollment.status = "enrolled"
            enrollment.completed_at = None
            enrollment.save(update_fields=["status", "completed_at"])

        notify.course_enrollment(enrollment, request)
        messages.success(request, f"{member.full_name} fue inscrito/a en el curso.")
        return redirect("course_detail", pk=course.pk)


enrollment_create = EnrollmentCreateView.as_view()


class EnrollmentCompleteView(ManageEducationRequiredMixin, View):
    """Mark an enrollment as completed (POST only). May issue a block
    certificate."""

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        enrollment = get_object_or_404(Enrollment, pk=pk, tenant=tenant)

        certificate = enrollment.mark_completed()
        if certificate and getattr(certificate, "just_issued", False):
            notify.certificate_issued(certificate, request)
        if certificate:
            messages.success(
                request,
                f"¡Curso completado! Se emitió el certificado del bloque "
                f"\"{enrollment.course.course_block.name}\".",
            )
        else:
            messages.success(request, "Curso marcado como completado.")
        return redirect("course_detail", pk=enrollment.course.pk)


enrollment_complete = EnrollmentCompleteView.as_view()


class EnrollmentDeleteView(ManageMembersRequiredMixin, View):
    """Drop a member's enrollment (POST only) — flips status to 'dropped'
    rather than deleting the row, to preserve history."""

    def post(self, request, pk):
        tenant = getattr(request.user, "tenant", None)
        enrollment = get_object_or_404(Enrollment, pk=pk, tenant=tenant)
        enrollment.status = "dropped"
        enrollment.save(update_fields=["status"])
        messages.success(request, "Se dio de baja la inscripción.")
        return redirect("course_detail", pk=enrollment.course.pk)


enrollment_delete = EnrollmentDeleteView.as_view()


# ============================================================
# CERTIFICATES
# ============================================================


class BlockCertificateDetailView(LoginRequiredMixin, DetailView):
    """Printable certificate for completing a course block."""

    model = BlockCertificate
    template_name = "education/block_certificate_detail.html"
    context_object_name = "certificate"

    def get_queryset(self):
        user = self.request.user
        tenant = getattr(user, "tenant", None)
        if not tenant:
            return BlockCertificate.objects.none()
        certificates = BlockCertificate.objects.filter(tenant=tenant)
        if user.can_view_roster:
            return certificates
        # Anyone else only gets their own.
        return certificates.filter(member_id=user.member_profile_id)


block_certificate_detail = BlockCertificateDetailView.as_view()


def _certificate_filename(certificate):
    from django.utils.text import slugify

    return "certificado-{}-{}.pdf".format(
        slugify(certificate.course_block.name) or "bloque",
        slugify(certificate.member.full_name) or "miembro",
    )


class BlockCertificatePdfView(BlockCertificateDetailView):
    """The same certificate as a downloadable PDF (same access rules as the
    printable page: staff, or its owner)."""

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse
        from django.urls import reverse

        from education.certificates import render_certificate_pdf

        certificate = self.get_object()
        verify_url = request.build_absolute_uri(
            reverse("certificate_verify", args=[certificate.certificate_number])
        )
        response = HttpResponse(
            render_certificate_pdf(certificate, verify_url), content_type="application/pdf"
        )
        disposition = "inline" if request.GET.get("inline") else "attachment"
        response["Content-Disposition"] = f'{disposition}; filename="{_certificate_filename(certificate)}"'
        return response


block_certificate_pdf = BlockCertificatePdfView.as_view()


def certificate_verify(request, number):
    """Public page: is this certificate number genuine? Shows only what is
    printed on the certificate itself. No login, so anyone holding a printed
    copy can check it."""
    from django.shortcuts import render

    certificate = (
        BlockCertificate.objects.filter(certificate_number__iexact=number.strip())
        .select_related("tenant", "member", "course_block")
        .first()
    )
    return render(
        request,
        "education/certificate_verify.html",
        {"certificate": certificate, "number": number},
        status=200 if certificate else 404,
    )
