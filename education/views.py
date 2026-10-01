"""
Course, course block, and enrollment views.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.mixins import ManageEducationRequiredMixin, ManageMembersRequiredMixin
from members.models import Member, User

from .models import BlockCertificate, Course, CourseBlock, Enrollment


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
        tenant = getattr(self.request.user, "tenant", None)
        course = self.object

        context["enrollments"] = course.enrollments.select_related("member").exclude(
            status="dropped"
        )
        if tenant:
            enrolled_member_ids = course.enrollments.exclude(
                status="dropped"
            ).values_list("member_id", flat=True)
            context["enrollable_members"] = Member.objects.filter(tenant=tenant).exclude(
                id__in=enrolled_member_ids
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

    def form_valid(self, form):
        tenant = getattr(self.request.user, "tenant", None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
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

        member_ids = (
            Enrollment.objects.filter(course_id__in=course_ids)
            .exclude(status="dropped")
            .values_list("member_id", flat=True)
            .distinct()
        )

        progress = []
        for member in Member.objects.filter(id__in=member_ids):
            completed = Enrollment.objects.filter(
                member=member, course_id__in=course_ids, status="completed"
            ).count()
            certificate = block.certificates.filter(member=member).first()
            progress.append(
                {
                    "member": member,
                    "completed": completed,
                    "total": total,
                    "certificate": certificate,
                }
            )

        context["courses"] = courses
        context["progress"] = progress
        return context


course_block_detail = CourseBlockDetailView.as_view()


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
        tenant = getattr(self.request.user, "tenant", None)
        if not tenant:
            return BlockCertificate.objects.none()
        return BlockCertificate.objects.filter(tenant=tenant)


block_certificate_detail = BlockCertificateDetailView.as_view()
