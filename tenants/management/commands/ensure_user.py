"""
Idempotently make sure a user exists in a tenant with a given role.

Safe to run on every container start: if the email already exists nothing is
changed (the password is never overwritten). Without --password a random one
is generated and printed once, so it can be read from the container logs.

Usage:
    python manage.py ensure_user suhellen@example.com \
        --first-name Suhellen --last-name Fallas --role admin --tenant oasisdevida
"""

import secrets

from django.core.management.base import BaseCommand, CommandError

from members.models import User
from tenants.models import Tenant


class Command(BaseCommand):
    help = "Create a user in a tenant with the given role, if it doesn't exist yet."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument(
            "--role", default="admin", choices=[r for r, _ in User.ROLE_CHOICES]
        )
        parser.add_argument(
            "--tenant", default=None, help="Tenant subdomain (default: the only tenant)"
        )
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        email = User.objects.normalize_email(options["email"])
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"User {email} already exists, nothing to do.")
            return

        tenants = Tenant.objects.all()
        if options["tenant"]:
            tenants = tenants.filter(subdomain=options["tenant"])
        if tenants.count() != 1:
            raise CommandError(
                "Pass --tenant with an existing subdomain "
                f"(found {tenants.count()} matching tenants)."
            )
        tenant = tenants.get()

        password = options["password"] or secrets.token_urlsafe(9)
        username = email.split("@")[0]
        if User.objects.filter(username=username).exists():
            username = f"{username}-{secrets.token_hex(2)}"

        User.objects.create_user(
            email=email,
            password=password,
            username=username,
            first_name=options["first_name"],
            last_name=options["last_name"],
            role=options["role"],
            tenant=tenant,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {options['role']} {email} in {tenant.subdomain}"
            )
        )
        if not options["password"]:
            self.stdout.write(f"Generated password for {email}: {password}")
