"""
E2E Tests: Courses, Events (requirements + attendance) and Finance dashboard.

Data is created through fixtures (pytest's main thread) and the tests drive the
UI only: the test bodies run on the Playwright worker thread, so they assert on
what the page shows rather than touching the ORM.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from education.models import Course, CourseBlock
from events.models import Event, EventRegistration
from finance.models import Donation, Expense
from members.models import Member

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


def _member(tenant, first, last, **kwargs):
    return Member.objects.create(
        tenant=tenant,
        first_name=first,
        last_name=last,
        email=f"{first.lower()}.{last.lower()}@e2e.test",
        member_status="member",
        **kwargs,
    )


@pytest.fixture
def ana(admin_user):
    return _member(admin_user.tenant, "Ana", "Mora", is_baptized=True)


@pytest.fixture
def carlos(admin_user):
    return _member(admin_user.tenant, "Carlos", "Solís")  # not baptized


@pytest.fixture
def block_with_course(admin_user):
    block = CourseBlock.objects.create(tenant=admin_user.tenant, name="Discipulado")
    course = Course.objects.create(
        tenant=admin_user.tenant, title="Fundamentos", course_block=block
    )
    return block, course


@pytest.fixture
def baptized_only_course(admin_user):
    return Course.objects.create(
        tenant=admin_user.tenant, title="Bautismo avanzado", requires_baptized=True
    )


@pytest.fixture
def upcoming_event(admin_user):
    return Event.objects.create(
        tenant=admin_user.tenant,
        title="Conferencia",
        start_at=timezone.now() + timedelta(days=5),
    )


@pytest.fixture
def baptized_only_event(admin_user):
    return Event.objects.create(
        tenant=admin_user.tenant,
        title="Encuentro de Bautizados",
        start_at=timezone.now() + timedelta(days=5),
        requires_baptized=True,
    )


@pytest.fixture
def past_event(admin_user, ana):
    event = Event.objects.create(
        tenant=admin_user.tenant,
        title="Culto de Domingo",
        start_at=timezone.now() - timedelta(days=2),
    )
    EventRegistration.objects.create(tenant=admin_user.tenant, member=ana, event=event)
    return event


@pytest.fixture
def finance_data(admin_user):
    Donation.objects.create(
        tenant=admin_user.tenant, amount=Decimal("150.00"), status="completed"
    )
    Expense.objects.create(
        tenant=admin_user.tenant,
        description="Luz del templo",
        amount=Decimal("45.00"),
        expense_date=timezone.localdate(),
    )


@pytest.mark.e2e
@pytest.mark.django_db
class TestCoursesE2E:
    def test_create_block_and_course_from_the_forms(
        self, page, live_server_url, admin_user
    ):
        """The block and prerequisite dropdowns must list real options."""
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/education/blocks/create/")
        page.fill("#name", "Formación de Líderes")
        page.click("button[type='submit']")
        assert "Formación de Líderes" in page.content()

        page.goto(f"{live_server_url}/education/create/")
        page.fill("#title", "Liderazgo 101")
        page.select_option("#course_block", label="Formación de Líderes")
        page.check("#requires_baptized")
        page.click("button[type='submit']")

        page.goto(f"{live_server_url}/education/")
        assert "Liderazgo 101" in page.content()

    def test_enroll_and_complete_issues_certificate(
        self, page, live_server_url, admin_user, ana, block_with_course
    ):
        block, course = block_with_course
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/education/{course.pk}/")
        page.select_option("select[name='member']", label=ana.full_name)
        page.click("button:has-text('Inscribir')")
        assert "fue inscrito/a en el curso" in page.content()

        page.click("button[title='Marcar completado']")
        assert "Se emitió el certificado" in page.content()

        # The block page links to the printable certificate.
        page.goto(f"{live_server_url}/education/blocks/{block.pk}/")
        page.click("a.btn-outline-success")
        assert "CERT-" in page.content()

    def test_unbaptized_member_is_rejected_with_a_reason(
        self, page, live_server_url, admin_user, carlos, baptized_only_course
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/education/{baptized_only_course.pk}/")
        page.select_option("select[name='member']", label=carlos.full_name)
        page.click("button:has-text('Inscribir')")

        assert "fue inscrito/a en el curso" not in page.content()
        assert "bautiz" in page.content().lower()


@pytest.mark.e2e
@pytest.mark.django_db
class TestEventsE2E:
    def test_create_event_with_requirements(self, page, live_server_url, admin_user):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/events/create/")
        page.fill("#title", "Retiro de Parejas")
        page.select_option("#event_type", "retreat")
        page.fill("#start_at", "2030-05-10T18:00")
        page.fill("#capacity", "40")
        page.check("#requires_married")
        page.click("button[type='submit']")

        page.goto(f"{live_server_url}/events/")
        assert "Retiro de Parejas" in page.content()

    def test_register_member_with_search(
        self, page, live_server_url, admin_user, ana, carlos, upcoming_event
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/events/{upcoming_event.pk}/")
        page.fill("#member-search", "carlos")
        # Only the matching member stays visible.
        assert page.locator(".member-option:visible").count() == 1
        page.click(".member-option:visible")

        assert "fue inscrito/a en el evento" in page.content()

    def test_requirement_blocks_registration(
        self, page, live_server_url, admin_user, ana, carlos, baptized_only_event
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/events/{baptized_only_event.pk}/")
        page.fill("#member-search", "solís")
        page.click(".member-option:visible")

        assert "fue inscrito/a en el evento" not in page.content()
        assert "bautiz" in page.content().lower()

    def test_take_attendance_on_a_past_event(
        self, page, live_server_url, admin_user, ana, carlos, past_event
    ):
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/events/{past_event.pk}/attendance/")
        page.fill("#live-search", "carlos")
        assert page.locator("tr.attendance-row:visible").count() == 1
        page.check(f"input.attendance-box[value='{carlos.pk}']")
        page.click("button:has-text('Guardar asistencia')")

        assert "Asistencia guardada: 1 presentes" in page.content()

        # The event page reflects who showed up; Ana registered but didn't come.
        page.goto(f"{live_server_url}/events/{past_event.pk}/")
        assert "no asistieron" in page.content()

    def test_attendance_report_loads(self, page, live_server_url, admin_user):
        _login(page, live_server_url, admin_user)
        page.goto(f"{live_server_url}/events/attendance/report/")
        assert "asistencia" in page.content().lower()


@pytest.mark.e2e
@pytest.mark.django_db
class TestFinanceDashboardE2E:
    def test_dashboard_with_donation_and_expense(
        self, page, live_server_url, admin_user, finance_data
    ):
        """Regression: the dashboard 500'd once both a donation and an expense
        existed."""
        _login(page, live_server_url, admin_user)

        response = page.goto(f"{live_server_url}/finance/")

        assert response.status == 200
        assert page.locator("#financeChart").count() == 1
        assert "Finanzas" in page.content()
