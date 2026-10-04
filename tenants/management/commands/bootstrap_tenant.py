"""
Idempotent first-run bootstrap for a standalone (single-church) install.

Unlike create_tenant, this is safe to run on every container start: it does
nothing if a tenant already exists. Configured entirely via environment
variables so it can run non-interactively (e.g. a Docker entrypoint).

Env vars:
    CHURCH_NAME       (default: "My Church")
    CHURCH_SUBDOMAIN  (default: "main")
    CHURCH_CURRENCY   (default: "USD", e.g. "CRC")
    CHURCH_TIMEZONE   (default: "America/New_York", e.g. "America/Costa_Rica")
    ADMIN_EMAIL       (optional — creates an admin user if set)
    ADMIN_PASSWORD    (required if ADMIN_EMAIL is set)
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from tenants.models import Tenant


class Command(BaseCommand):
    help = "Create the single tenant for a standalone install, if none exists yet."

    def handle(self, *args, **options):
        if Tenant.objects.exists():
            self.stdout.write("A tenant already exists, nothing to bootstrap.")
            return

        name = os.environ.get("CHURCH_NAME", "My Church")
        subdomain = os.environ.get("CHURCH_SUBDOMAIN", "main")
        admin_email = os.environ.get("ADMIN_EMAIL")
        admin_password = os.environ.get("ADMIN_PASSWORD")

        create_args = [name, subdomain]
        create_kwargs = {}
        if os.environ.get("CHURCH_CURRENCY"):
            create_kwargs["currency"] = os.environ["CHURCH_CURRENCY"]
        if os.environ.get("CHURCH_TIMEZONE"):
            create_kwargs["timezone"] = os.environ["CHURCH_TIMEZONE"]
        if admin_email:
            create_kwargs["admin_email"] = admin_email
            create_kwargs["admin_password"] = admin_password

        call_command("create_tenant", *create_args, **create_kwargs)
