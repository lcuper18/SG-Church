"""allauth adapters."""

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class AccountAdapter(DefaultAccountAdapter):
    def get_client_ip(self, request):
        """The address the login-attempt limits count against.

        allauth's default trusts the first X-Forwarded-For entry, which the client writes
        itself: sending a different fake one with every attempt would defeat the per-address
        limit. The trustworthy entry is the one our own proxy appended, i.e. the last
        (TRUSTED_PROXY_COUNT = 1 in production). With 0 proxies the header is ignored."""
        hops = settings.TRUSTED_PROXY_COUNT
        forwarded = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if hops and len(forwarded) >= hops:
            return forwarded[-hops]
        return request.META.get("REMOTE_ADDR", "")
