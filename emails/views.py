from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .unsubscribe import member_for


@csrf_exempt  # mail apps POST here ("one-click" unsubscribe); the signed token is the credential
@require_http_methods(["GET", "POST"])
def unsubscribe(request, token):
    """Public page behind the footer link. GET only asks for confirmation (mail
    scanners open links, so a GET must never change anything); POST does it."""
    member = member_for(token)
    if member is None:
        return render(request, "emails/unsubscribe.html", {"invalid": True}, status=404)
    done = None
    if request.method == "POST":
        wanted = request.POST.get("action") != "resubscribe"
        if member.email_opt_out != wanted:
            member.email_opt_out = wanted
            member.save(update_fields=["email_opt_out"])
        done = "unsubscribed" if wanted else "resubscribed"
    return render(request, "emails/unsubscribe.html", {"member": member, "done": done})
