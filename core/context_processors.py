from django.conf import settings


def support_donations(request):
    """Expose the PayPal button used to support the software's development."""
    client_id = settings.PAYPAL_SUPPORT_CLIENT_ID
    button_id = settings.PAYPAL_SUPPORT_BUTTON_ID
    if not (client_id and button_id):
        return {"support_paypal": None}
    return {"support_paypal": {"client_id": client_id, "button_id": button_id}}
