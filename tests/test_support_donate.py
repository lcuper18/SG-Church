"""Footer PayPal button that supports the software's development."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_button_is_shown_by_default(client):
    html = client.get(reverse("login")).content.decode()
    assert "paypal.com/sdk/js" in html
    assert "paypal-container-" in html


@pytest.mark.django_db
def test_button_hidden_when_not_configured(client, settings):
    settings.PAYPAL_SUPPORT_BUTTON_ID = ""
    html = client.get(reverse("login")).content.decode()
    assert "paypal.com/sdk/js" not in html
