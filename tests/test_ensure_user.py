"""ensure_user management command: idempotent creation of a user in a tenant."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from members.models import User


def test_creates_admin_with_generated_password(tenant, capsys):
    call_command(
        "ensure_user", "suhellen@example.com",
        first_name="Suhellen", last_name="Fallas", role="admin", tenant=tenant.subdomain,
    )
    user = User.objects.get(email="suhellen@example.com")
    assert user.role == "admin"
    assert user.tenant == tenant
    assert user.get_full_name() == "Suhellen Fallas"
    assert user.can_manage_finance and user.can_manage_education
    password = capsys.readouterr().out.split("Generated password for")[1].split(": ")[1].strip()
    assert user.check_password(password)


def test_is_idempotent_and_keeps_password(tenant):
    call_command("ensure_user", "a@example.com", tenant=tenant.subdomain, password="Secret-123")
    call_command("ensure_user", "A@example.com", tenant=tenant.subdomain, password="Other-456")
    assert User.objects.filter(email__iexact="a@example.com").count() == 1
    assert User.objects.get(email="a@example.com").check_password("Secret-123")


def test_unknown_tenant_is_an_error(tenant):
    with pytest.raises(CommandError):
        call_command("ensure_user", "b@example.com", tenant="does-not-exist")
