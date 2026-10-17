"""
Guards against N+1 queries: a page must cost the same number of queries
whether it lists a few rows or many.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from education.models import Course, CourseBlock, Enrollment
from events.models import Event, EventRegistration
from finance.models import Donation
from members.models import Family, Member


@pytest.fixture
def tenant(admin_user):
    admin_user.tenant.onboarding_completed = True
    admin_user.tenant.save()
    return admin_user.tenant


@pytest.fixture
def client(admin_user):
    client = Client()
    client.force_login(admin_user)
    return client


def queries(client, url):
    with CaptureQueriesContext(connection) as captured:
        response = client.get(url)
    assert response.status_code == 200
    return len(captured)


def person(tenant, index, **kwargs):
    return Member.objects.create(tenant=tenant, first_name=f"P{index}", last_name="Prueba", **kwargs)


@pytest.mark.django_db
def test_event_list_cost_does_not_grow_with_events(client, tenant):
    def add_events(count, offset=0):
        for index in range(count):
            event = Event.objects.create(
                tenant=tenant, title=f"Evento {offset + index}",
                start_at=timezone.now() + timedelta(days=index + 1),
            )
            EventRegistration.objects.create(tenant=tenant, member=person(tenant, offset + index), event=event)
            event.required_courses.add(Course.objects.create(tenant=tenant, title=f"C{offset + index}"))

    add_events(2)
    few = queries(client, reverse("event_list"))
    add_events(10, offset=100)
    many = queries(client, reverse("event_list"))

    assert few == many


@pytest.mark.django_db
def test_event_list_shows_registered_counts_and_paginates(client, tenant):
    event = Event.objects.create(tenant=tenant, title="Con inscritos", start_at=timezone.now() + timedelta(days=1))
    for index in range(3):
        EventRegistration.objects.create(tenant=tenant, member=person(tenant, index), event=event)
    EventRegistration.objects.create(tenant=tenant, member=person(tenant, 9), event=event, status="cancelled")
    for index in range(30):
        Event.objects.create(tenant=tenant, title=f"Otro {index}", start_at=timezone.now() + timedelta(days=index + 2))

    response = client.get(reverse("event_list"))

    assert len(response.context["events"]) == 25
    first = next(e for e in response.context["events"] if e.title == "Con inscritos")
    assert first.registered_count == 3
    assert len(client.get(reverse("event_list"), {"page": 2}).context["events"]) == 6


@pytest.mark.django_db
def test_family_list_cost_does_not_grow_with_families(client, tenant):
    def add_families(count, offset=0):
        for index in range(count):
            head = person(tenant, offset + index)
            family = Family.objects.create(tenant=tenant, name=f"F{offset + index}", head_of_family=head)
            head.family = family
            head.save()

    add_families(2)
    few = queries(client, reverse("family_list"))
    add_families(12, offset=100)
    many = queries(client, reverse("family_list"))

    assert few == many


@pytest.mark.django_db
def test_block_progress_cost_does_not_grow_with_students(client, tenant):
    block = CourseBlock.objects.create(tenant=tenant, name="Discipulado")
    courses = [Course.objects.create(tenant=tenant, title=f"C{i}", course_block=block) for i in range(3)]

    def add_students(count, offset=0):
        for index in range(count):
            student = person(tenant, offset + index)
            for course in courses:
                Enrollment.objects.create(tenant=tenant, member=student, course=course)
            for enrollment in student.enrollments.all():
                enrollment.mark_completed()

    add_students(2)
    url = reverse("course_block_detail", args=[block.pk])
    few = queries(client, url)
    add_students(10, offset=100)
    many = queries(client, url)

    assert few == many
    rows = client.get(url).context["progress"]
    assert len(rows) == 12
    assert all(row["completed"] == 3 and row["certificate"] for row in rows)


@pytest.mark.django_db
def test_block_progress_counts_partial_work_and_ignores_dropped(client, tenant):
    block = CourseBlock.objects.create(tenant=tenant, name="Discipulado")
    one, two = (Course.objects.create(tenant=tenant, title=t, course_block=block) for t in ("Uno", "Dos"))
    ana, beto = person(tenant, 1), person(tenant, 2)
    Enrollment.objects.create(tenant=tenant, member=ana, course=one).mark_completed()
    Enrollment.objects.create(tenant=tenant, member=ana, course=two)
    Enrollment.objects.create(tenant=tenant, member=beto, course=one, status="dropped")

    rows = client.get(reverse("course_block_detail", args=[block.pk])).context["progress"]

    assert [(r["member"], r["completed"], r["total"], r["certificate"]) for r in rows] == [(ana, 1, 2, None)]


@pytest.mark.django_db
def test_finance_dashboard_has_a_small_constant_cost(client, tenant):
    for months_back in range(14):
        Donation.objects.create(tenant=tenant, amount=Decimal("100"), status="completed")
    few = queries(client, reverse("finance_dashboard"))
    for _ in range(30):
        Donation.objects.create(tenant=tenant, amount=Decimal("5"), status="completed")
    many = queries(client, reverse("finance_dashboard"))

    assert few == many <= 12


@pytest.mark.django_db
def test_finance_dashboard_totals_by_month(client, tenant):
    from finance.models import Expense

    today = timezone.localdate()
    Donation.objects.create(tenant=tenant, amount=Decimal("100.00"), status="completed")
    Donation.objects.create(tenant=tenant, amount=Decimal("50.00"), status="pending")
    Expense.objects.create(tenant=tenant, description="Luz", amount=Decimal("30.00"), expense_date=today)

    context = client.get(reverse("finance_dashboard")).context

    assert context["donations_this_month"] == Decimal("100.00")
    assert context["expenses_this_month"] == Decimal("30.00")
    assert context["balance_this_month"] == Decimal("70.00")
    assert len(context["chart_data"]) == 12
    assert context["chart_data"][-1]["donations"] == 100.0
    assert context["chart_data"][-1]["expenses"] == 30.0
    assert sum(point["donations"] for point in context["chart_data"][:-1]) == 0


@pytest.mark.django_db
def test_event_list_puts_upcoming_events_first_then_the_latest_past_ones(client, tenant):
    now = timezone.now()
    for title, days in (("Pasado viejo", -30), ("Pasado reciente", -2), ("Lejano", 20), ("Cercano", 3)):
        Event.objects.create(tenant=tenant, title=title, start_at=now + timedelta(days=days))

    titles = [e.title for e in client.get(reverse("event_list")).context["events"]]

    assert titles == ["Cercano", "Lejano", "Pasado reciente", "Pasado viejo"]


@pytest.mark.django_db
def test_donor_report_paginates_and_includes_the_last_day(client, tenant):
    for index in range(60):
        Donation.objects.create(
            tenant=tenant, member=person(tenant, index), amount=Decimal("10"), status="completed"
        )
    today = timezone.localdate().isoformat()

    page_one = client.get(reverse("donations_by_member")).context["donations_by_member"]
    assert len(page_one) == 50
    assert len(client.get(reverse("donations_by_member"), {"page": 2}).context["donations_by_member"]) == 10

    # A donation made today still counts when the range ends today.
    same_day = client.get(reverse("donations_by_member"), {"date_from": today, "date_to": today})
    assert same_day.context["donations_by_member"].paginator.count == 60
