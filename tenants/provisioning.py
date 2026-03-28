"""
Tenant provisioning service.
Handles schema creation, migration, and teardown for tenants.
"""

from django.db import connection, connections
from django.core.management import call_command
from tenants.models import Tenant
import logging

logger = logging.getLogger(__name__)


class TenantProvisioningError(Exception):
    """Exception raised for tenant provisioning errors."""

    pass


class TenantProvisioner:
    """
    Handles provisioning of tenant schemas in PostgreSQL.
    """

    # Tables that exist in the public schema (shared tables)
    PUBLIC_TABLES = ["tenants", "tenantdomains", "django_site"]

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.schema_name = tenant.schema_name

    def create_schema(self):
        """
        Create a new PostgreSQL schema for the tenant.
        """
        if self.schema_exists():
            raise TenantProvisioningError(f"Schema {self.schema_name} already exists")

        with connections["default"].cursor() as cursor:
            # Create schema
            cursor.execute(f"CREATE SCHEMA {self.schema_name}")
            logger.info(f"Created schema: {self.schema_name}")

    def drop_schema(self):
        """
        Drop the tenant's schema and all its contents.
        WARNING: This is irreversible!
        """
        if not self.schema_exists():
            logger.warning(f"Schema {self.schema_name} does not exist")
            return

        with connections["default"].cursor() as cursor:
            # Drop schema (cascade drops all objects)
            cursor.execute(f"DROP SCHEMA {self.schema_name} CASCADE")
            logger.info(f"Dropped schema: {self.schema_name}")

    def schema_exists(self) -> bool:
        """Check if the tenant's schema exists."""
        with connections["default"].cursor() as cursor:
            cursor.execute(
                """
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """,
                [self.schema_name],
            )
            return cursor.fetchone() is not None

    def run_migrations(self):
        """
        Run Django migrations for the tenant's schema.
        """
        # Set schema for migrations
        old_schema = connection.schema_name

        try:
            connection.set_schema(self.schema_name)

            # Run migrations for all apps
            call_command(
                "migrate",
                verbosity=2,
                interactive=False,
                run_syncdb=True,
            )
            logger.info(f"Migrations completed for schema: {self.schema_name}")

        finally:
            connection.set_schema(old_schema)

    def seed_default_data(self):
        """
        Seed default data for a new tenant.
        """
        # Set schema
        old_schema = connection.schema_name

        try:
            connection.set_schema(self.schema_name)

            # Create default roles/groups if needed
            # Create default account types if needed

            logger.info(f"Default data seeded for schema: {self.schema_name}")

        finally:
            connection.set_schema(old_schema)

    def provision(self):
        """
        Full provisioning: create schema + run migrations + seed data.
        """
        logger.info(f"Provisioning tenant: {self.tenant.name}")

        # Step 1: Create schema
        self.create_schema()

        # Step 2: Run migrations
        self.run_migrations()

        # Step 3: Seed default data
        self.seed_default_data()

        logger.info(f"Provisioning complete for: {self.tenant.name}")

        return {"schema": self.schema_name, "status": "provisioned"}

    def get_table_list(self):
        """Get list of tables in tenant's schema."""
        with connections["default"].cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """,
                [self.schema_name],
            )
            return [row[0] for row in cursor.fetchall()]

    def get_table_count(self) -> int:
        """Get count of tables in tenant's schema."""
        return len(self.get_table_list())


def provision_tenant(tenant: Tenant) -> dict:
    """
    Convenience function to provision a tenant.
    """
    provisioner = TenantProvisioner(tenant)
    return provisioner.provision()


def deprovision_tenant(tenant: Tenant) -> dict:
    """
    Convenience function to deprovision a tenant.
    WARNING: This deletes all tenant data!
    """
    provisioner = TenantProvisioner(tenant)
    provisioner.drop_schema()

    return {"schema": tenant.schema_name, "status": "deprovisioned"}


def get_tenant_schema_names() -> list:
    """Get all tenant schema names."""
    with connections["default"].cursor() as cursor:
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name LIKE 'tenant_%'
            ORDER BY schema_name
        """)
        return [row[0] for row in cursor.fetchall()]


def get_tenant_stats(tenant: Tenant) -> dict:
    """Get statistics for a tenant's schema."""
    provisioner = TenantProvisioner(tenant)

    return {
        "schema_exists": provisioner.schema_exists(),
        "table_count": provisioner.get_table_count(),
        "tables": provisioner.get_table_list(),
    }
