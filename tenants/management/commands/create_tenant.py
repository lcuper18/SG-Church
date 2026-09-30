"""
Create a tenant (church) from the command line.

Usage:
    python manage.py create_tenant "Iglesia Central" iglesiacentral
    python manage.py create_tenant "Iglesia Central" iglesiacentral \\
        --admin-email admin@example.com --admin-password changeme123

This is the scriptable equivalent of the web onboarding wizard
(/onboarding/) — handy for a standalone install's first-run setup, where
nobody is available to click through a browser yet.
"""

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from members.models import User
from tenants.models import Tenant


class Command(BaseCommand):
    help = "Create a tenant (church), optionally with its first admin user."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Church name, e.g. 'Iglesia Central'")
        parser.add_argument(
            "subdomain",
            help="Subdomain slug for this church, e.g. 'iglesiacentral'",
        )
        parser.add_argument(
            "--admin-email", default=None, help="Create an admin user with this email"
        )
        parser.add_argument(
            "--admin-password",
            default=None,
            help="Password for the admin user (required if --admin-email is given)",
        )

    def handle(self, *args, **options):
        name = options["name"]
        subdomain = options["subdomain"].strip().lower()
        admin_email = options["admin_email"]
        admin_password = options["admin_password"]

        if not re.fullmatch(r"[a-z0-9-]+", subdomain):
            raise CommandError(
                "subdomain must contain only lowercase letters, digits, and hyphens"
            )

        if Tenant.objects.filter(subdomain=subdomain).exists():
            raise CommandError(f"A tenant with subdomain '{subdomain}' already exists")

        if admin_email and not admin_password:
            raise CommandError("--admin-password is required when --admin-email is set")

        with transaction.atomic():
            tenant = Tenant.objects.create(
                name=name,
                subdomain=subdomain,
                onboarding_completed=True,
            )

            if admin_email:
                if User.objects.filter(email=admin_email).exists():
                    raise CommandError(f"A user with email '{admin_email}' already exists")
                User.objects.create_user(
                    email=admin_email,
                    password=admin_password,
                    role="admin",
                    tenant=tenant,
                )

        self.stdout.write(self.style.SUCCESS(f"Created tenant '{tenant.name}' ({tenant.subdomain})"))
        if admin_email:
            self.stdout.write(self.style.SUCCESS(f"Created admin user {admin_email}"))
