"""
E2E Tests: the support link is quiet, and opens a small dialog on request.
"""

import pytest


@pytest.mark.e2e
@pytest.mark.django_db
class TestSupportLinkE2E:
    def test_link_opens_and_closes_a_dialog(self, page, live_server_url):
        page.route("**/paypal.com/**", lambda route: route.abort())  # no network in tests
        page.goto(f"{live_server_url}/accounts/login/")
        assert not page.is_visible("#supportModal")
        assert page.locator("footer").bounding_box()["height"] < 120  # a slim footer
        page.click(".support-link")
        page.wait_for_selector("#supportModal.show")
        assert "No es una ofrenda para tu iglesia" in page.inner_text("#supportModal")
        page.wait_for_timeout(600)  # Bootstrap ignores a close that arrives mid-animation
        page.click("#supportModal .btn-close")
        page.wait_for_selector("#supportModal", state="hidden")
