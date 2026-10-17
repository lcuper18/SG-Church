"""
E2E Tests: importing members from a CSV file through the browser.
"""

import pytest

PASSWORD = "testpassword123"


def _login(page, live_server_url, user):
    page.goto(f"{live_server_url}/accounts/login/")
    page.fill("#id_login", user.email)
    page.fill("#id_password", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(lambda url: "/accounts/login/" not in url)


@pytest.mark.e2e
@pytest.mark.django_db
class TestMemberImportE2E:
    def test_upload_review_and_confirm(self, page, live_server_url, admin_user, tmp_path):
        sheet = tmp_path / "gente.csv"
        sheet.write_text(
            "Nombre;Apellido;Email;Fecha de nacimiento;Familia;Etiquetas\n"
            "Lucía;Fernández;lucia@e2e.test;17/05/1990;Familia Fernández;Coro\n"
            "Mateo;Fernández;mateo@e2e.test;02/03/2015;Familia Fernández;\n"
            "Sin;Correo;mal-correo;;;\n",
            encoding="cp1252",
        )
        _login(page, live_server_url, admin_user)

        page.goto(f"{live_server_url}/members/")
        page.click("a:has-text('Importar CSV')")
        page.set_input_files("#file", str(sheet))
        page.click("button:has-text('Revisar archivo')")

        assert page.inner_text("#count-create") == "2"
        assert page.inner_text("#count-error") == "1"
        assert "Correo no válido" in page.content()

        page.click("button:has-text('Importar 2 personas')")

        content = page.content()
        assert "Importación lista: 2 nuevos" in content
        assert "Lucía Fernández" in content and "Mateo Fernández" in content
        assert "Sin Correo" not in content

        page.goto(f"{live_server_url}/members/families/")
        assert "Familia Fernández" in page.content()
