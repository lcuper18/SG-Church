"""
List all tenants (churches) registered in this install.

Usage:
    python manage.py list_tenants
"""

from django.core.management.base import BaseCommand

from tenants.models import Tenant


class Command(BaseCommand):
    help = "List all tenants (churches) in this install."

    def handle(self, *args, **options):
        tenants = Tenant.objects.order_by("name")

        if not tenants:
            self.stdout.write("No tenants yet. Create one with 'python manage.py create_tenant'.")
            return

        for tenant in tenants:
            status = "active" if tenant.is_active else "inactive"
            self.stdout.write(
                f"{tenant.subdomain:<30} {tenant.name:<40} {status:<10} "
                f"members={tenant.members.count()}"
            )
