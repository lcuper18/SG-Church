"""
E2E Tests: adding and removing a block's courses from the block page.
"""

import pytest

from education.models import Course, CourseBlock


@pytest.fixture
def block_and_loose_course(admin_user):
    block = CourseBlock.objects.create(tenant=admin_user.tenant, name="Discipulado")
    Course.objects.create(tenant=admin_user.tenant, title="Curso suelto")
    return block


@pytest.mark.e2e
@pytest.mark.django_db
class TestBlockCoursesE2E:
    def _login(self, page, live_server_url, user):
        page.goto(f"{live_server_url}/accounts/login/")
        page.fill("#id_login", user.email)
        page.fill("#id_password", "testpassword123")
        page.click("button[type='submit']")
        page.wait_for_url(lambda url: "/accounts/login/" not in url)

    def test_add_then_remove_a_course_from_the_block_page(
        self, page, live_server_url, admin_user, block_and_loose_course
    ):
        block = block_and_loose_course
        self._login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/education/blocks/{block.pk}/")
        page.select_option("#add-course", label="Curso suelto")
        page.click("button:has-text('Agregar')")
        assert "se agregó al bloque" in page.content()
        assert page.locator("ul.list-group a:has-text('Curso suelto')").count() == 1

        page.click("button[title='Quitar del bloque']")
        assert "ya no pertenece al bloque" in page.content()
        assert page.locator("ul.list-group a:has-text('Curso suelto')").count() == 0

    def test_create_a_new_course_from_the_block_and_land_back_on_it(
        self, page, live_server_url, admin_user, block_and_loose_course
    ):
        block = block_and_loose_course
        self._login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/education/blocks/{block.pk}/")
        page.click("a:has-text('Crear curso nuevo en este bloque')")
        page.fill("#title", "Curso desde el bloque")
        assert page.input_value("#course_block") == str(block.pk)  # preselected
        page.click("button[type='submit']")

        assert page.url.rstrip("/").endswith(str(block.pk))
        assert page.locator("ul.list-group a:has-text('Curso desde el bloque')").count() == 1
