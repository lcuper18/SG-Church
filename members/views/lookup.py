"""JSON type-ahead used by the pick-a-person boxes."""

import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import View

from ..models import Member
from ..search import search_members


class MemberLookupView(LoginRequiredMixin, View):
    """JSON search used by the "pick a person" boxes (register for an event,
    enrol in a course, choose a family's members), so those pages don't ship the
    whole directory in their HTML. Names only (plus e-mail and family), and
    only for roles that already see people's names in their daily work."""

    LIMIT = 15
    MAX_LIMIT = 30

    @staticmethod
    def _uuid(value):
        try:
            return uuid.UUID(value) if value else None
        except ValueError:
            return None

    def get(self, request):
        user = request.user
        tenant = getattr(user, "tenant", None)
        if tenant is None or not (
            user.can_manage_members or user.can_manage_education or user.can_manage_finance
        ):
            return JsonResponse({"results": [], "total": 0}, status=403)

        people = search_members(Member.objects.filter(tenant=tenant), request.GET.get("q", ""))

        from education.models import Enrollment
        from events.models import EventRegistration

        # Hide people who are already in the event/course being edited. A bad id
        # just means "exclude nobody".
        event_id = self._uuid(request.GET.get("exclude_event"))
        if event_id:
            people = people.exclude(
                id__in=EventRegistration.objects.filter(
                    event_id=event_id, tenant=tenant, status="registered"
                ).values("member_id")
            )
        course_id = self._uuid(request.GET.get("exclude_course"))
        if course_id:
            people = people.exclude(
                id__in=Enrollment.objects.filter(
                    course_id=course_id, tenant=tenant, status__in=["enrolled", "completed"]
                ).values("member_id")
            )

        try:
            limit = min(max(int(request.GET.get("limit", self.LIMIT)), 1), self.MAX_LIMIT)
        except ValueError:
            limit = self.LIMIT
        total = people.count()
        rows = people.select_related("family").order_by("last_name", "first_name")[:limit]
        return JsonResponse(
            {
                "total": total,
                "results": [
                    {
                        "id": str(person.pk),
                        "name": person.full_name,
                        "email": person.email or "",
                        "id_hint": person.national_id_hint,
                        "family": person.family.name if person.family else "",
                        "family_id": str(person.family_id) if person.family_id else "",
                    }
                    for person in rows
                ],
            }
        )


member_lookup = MemberLookupView.as_view()
