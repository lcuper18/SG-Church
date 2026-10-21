"""Public donation page and Stripe checkout."""

import stripe
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from members.models import Member

from ..models import Donation


def donate_page(request):
    """Public donation page."""

    # Get tenant from subdomain or query param
    tenant = None
    subdomain = request.GET.get("church")

    if subdomain:
        from tenants.models import Tenant

        tenant = Tenant.objects.filter(subdomain=subdomain, is_active=True).first()

    if not tenant and request.user.is_authenticated:
        tenant = getattr(request.user, "tenant", None)

    if not tenant:
        return render(
            request, "finance/donate.html", {"error": "Iglesia no encontrada"}
        )

    context = {
        "tenant": tenant,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, "finance/donate.html", context)


def create_checkout_session(request):
    """Create Stripe checkout session for donation."""

    if request.method != "POST":
        return redirect("donate_page")

    import json

    from tenants.models import Tenant

    # Get tenant
    tenant = None
    subdomain = request.POST.get("church")
    if subdomain:
        tenant = Tenant.objects.filter(subdomain=subdomain, is_active=True).first()

    if not tenant and request.user.is_authenticated:
        tenant = getattr(request.user, "tenant", None)

    if not tenant:
        messages.error(request, "Iglesia no encontrada")
        return redirect("donate_page")

    # Get form data
    try:
        amount = float(request.POST.get("amount", 0))
    except ValueError:
        messages.error(request, "Monto inválido")
        return redirect("donate_page")
    campaign = request.POST.get("campaign", "offering")
    donor_name = request.POST.get("donor_name", "")
    donor_email = request.POST.get("donor_email", "")
    cover_fees = request.POST.get("cover_fees") == "on"

    # Sanity bounds before this ever reaches Stripe: guards against typos and
    # abusive input, not a business rule.
    MIN_DONATION_AMOUNT = 1
    MAX_DONATION_AMOUNT = 100_000
    if not (MIN_DONATION_AMOUNT <= amount <= MAX_DONATION_AMOUNT):
        messages.error(
            request,
            f"El monto debe estar entre {MIN_DONATION_AMOUNT} y {MAX_DONATION_AMOUNT}",
        )
        return redirect("donate_page")

    # Calculate fees (Stripe: 2.9% + $0.30)
    if cover_fees:
        fees = (amount * 0.029) + 0.30
        amount += fees

    # Convert to cents
    amount_cents = int(amount * 100)

    # Initialize Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": tenant.currency.lower(),
                        "product_data": {
                            "name": f"Donación - {tenant.name}",
                            "description": campaign.capitalize(),
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=request.build_absolute_uri("/donate/success/")
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri("/donate/"),
            metadata={
                "tenant_id": str(tenant.id),
                "campaign": campaign,
                "donor_name": donor_name,
                "donor_email": donor_email,
            },
        )

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        messages.error(request, f"Error al procesar pago: {str(e)}")
        return redirect("donate_page")


def donation_success(request):
    """Success page after donation."""

    session_id = request.GET.get("session_id")

    context = {
        "session_id": session_id,
    }

    return render(request, "finance/donate_success.html", context)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks.

    Exempt from CSRF because Stripe never sends a CSRF token; the request is
    instead authenticated by verifying the Stripe-Signature header below.
    """

    if request.method != "POST":
        return HttpResponse(status=405)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_session(session)
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        handle_payment_failed(invoice)

    return HttpResponse(status=200)


def handle_checkout_session(session):
    """Process completed checkout session."""

    metadata = session.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    campaign = metadata.get("campaign", "offering")
    donor_name = metadata.get("donor_name", "")
    donor_email = metadata.get("donor_email", "")

    if not tenant_id:
        return

    # Find or create member based on email
    member = None
    if donor_email:
        from members.models import Member

        member = Member.objects.filter(
            tenant_id=tenant_id, email__iexact=donor_email
        ).first()

    # Get amount
    amount = session.get("amount_total", 0) / 100

    # Create donation record
    donation = Donation.objects.create(
        tenant_id=tenant_id,
        member=member,
        amount=amount,
        currency=session.get("currency", "usd").upper(),
        campaign=campaign,
        status="completed",
        stripe_payment_intent_id=session.get("payment_intent", ""),
        donor_name=donor_name or (member.full_name if member else "Anonymous"),
        donor_email=donor_email or "",
    )

    # In-app notification for church admins. Kept apart from the receipt below
    # so a failure in one never silently skips the other.
    try:
        from django.contrib.auth import get_user_model

        from notifications.models import create_notification
        from tenants.models import Tenant

        tenant = Tenant.objects.get(id=tenant_id)

        # Get church admins
        admins = get_user_model().objects.filter(tenant=tenant, is_staff=True)

        campaign_display = dict(Donation.CAMPAIGN_CHOICES).get(
            campaign, campaign.title()
        )

        for admin in admins:
            create_notification(
                tenant=tenant,
                user=admin,
                title="Nueva donación recibida",
                message=f"Se recibió una donación de ${amount:.2f} ({campaign_display})",
                notification_type="donation_received",
                link=f"/finance/donations/{donation.pk}/",
                content_type="finance.donation",
                object_id=donation.pk,
            )
    except Exception as e:
        # Log error but don't break the donation flow
        import logging

        logging.exception(f"Error creating donation notification: {e}")

    # Receipt e-mail to the donor, asynchronously.
    try:
        from emails.tasks import send_donation_receipt_task

        send_donation_receipt_task.delay(donation.pk)
    except Exception as e:
        import logging

        logging.exception(f"Error queueing donation receipt: {e}")


def handle_payment_failed(invoice):
    """Handle failed payment."""

    # Find and update donation
    # This would need to match based on Stripe customer info
    pass
