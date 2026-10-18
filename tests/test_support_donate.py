"""Discreet footer link that opens the PayPal button supporting the software's development."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_footer_has_a_small_link_not_the_button(client):
    html = client.get(reverse("login")).content.decode()
    assert "Apoyar el proyecto" in html
    assert 'id="supportModal"' in html
    # Nothing from PayPal is loaded until someone opens it.
    assert '<script src="https://www.paypal.com' not in html
    assert "paypal-container-" in html  # the (empty) place the button is rendered into


@pytest.mark.django_db
def test_hidden_when_not_configured(client, settings):
    settings.PAYPAL_SUPPORT_BUTTON_ID = ""
    html = client.get(reverse("login")).content.decode()
    assert "Apoyar el proyecto" not in html and "supportModal" not in html
