"""
User management for church administrators: create logins, change roles,
reset passwords, activate/deactivate - always inside their own church.
"""

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from members.models import User
from tenants.models import Tenant

STRONG = "Clave-Segura-2026"


def _other_tenant_user(role="admin", **kwargs):
    tenant = Tenant.objects.create(name="Otra", subdomain=f"otra-{uuid.uuid4().hex[:6]}")
    return User.objects.create_user(
        email=f"x-{uuid.uuid4().hex[:6]}@otra.com", password=STRONG, role=role,
        tenant=tenant, **kwargs,
    )


def _new_user_data(**overrides):
    data = {
        "first_name": "Suhellen", "last_name": "Fallas", "email": "suhellen@iglesia.test",
        "role": "treasurer", "password1": STRONG, "password2": STRONG,
    }
    data.update(overrides)
    return data


def _can_log_in(email, password):
    response = Client().post(reverse("login"), {"login": email, "password": password})
    return response.status_code == 302 and response.url == "/dashboard/"


@pytest.mark.django_db
class TestAccess:
    URLS = ["user_list", "user_create"]

    def test_anonymous_is_sent_to_login(self, client):
        for name in self.URLS:
            response = client.get(reverse(name))
            assert response.status_code == 302 and "login" in response.url

    @pytest.mark.parametrize("role", ["pastor", "treasurer", "teacher", "volunteer", "member"])
    def test_non_admin_roles_get_403(self, role, admin_user):
        user = User.objects.create_user(
            email=f"{role}@t.com", password=STRONG, role=role, tenant=admin_user.tenant
        )
        client = Client()
        client.force_login(user)
        target = User.objects.create_user(
            email="t@t.com", password=STRONG, tenant=admin_user.tenant
        )
        assert client.get(reverse("user_list")).status_code == 403
        assert client.get(reverse("user_create")).status_code == 403
        assert client.get(reverse("user_update", args=[target.pk])).status_code == 403
        assert client.post(reverse("user_toggle_active", args=[target.pk])).status_code == 403
        target.refresh_from_db()
        assert target.is_active

    def test_menu_link_only_for_admins(self, authenticated_client, regular_user):
        # Own Client for the regular user: the shared `client` fixture would
        # otherwise end up logged in as whoever logged in last.
        regular = Client()
        regular.force_login(regular_user)
        assert reverse("user_list") in authenticated_client.get(reverse("profile")).content.decode()
        assert reverse("user_list") not in regular.get(reverse("profile")).content.decode()


@pytest.mark.django_db
class TestList:
    def test_lists_only_this_churchs_non_superusers(self, authenticated_client, admin_user):
        mine = User.objects.create_user(
            email="mia@t.com", password=STRONG, tenant=admin_user.tenant,
            first_name="Mía", last_name="Propia",
        )
        theirs = _other_tenant_user(first_name="Ajeno", last_name="Otro")
        root = User.objects.create_user(
            email="root@t.com", password=STRONG, tenant=admin_user.tenant,
            first_name="Super", last_name="Usuario", is_superuser=True,
        )

        users = list(authenticated_client.get(reverse("user_list")).context["church_users"])

        assert mine in users and admin_user in users
        assert theirs not in users and root not in users


@pytest.mark.django_db
class TestCreate:
    def test_creates_user_in_admins_church_who_can_log_in(
        self, authenticated_client, admin_user
    ):
        other = Tenant.objects.create(name="Otra", subdomain="otra-create")

        response = authenticated_client.post(
            reverse("user_create"), {**_new_user_data(), "tenant": str(other.pk)}
        )

        assert response.status_code == 302
        created = User.objects.get(email="suhellen@iglesia.test")
        assert created.tenant == admin_user.tenant  # never taken from the POST
        assert created.role == "treasurer" and created.can_manage_finance
        assert not created.is_superuser and not created.is_staff
        assert _can_log_in("suhellen@iglesia.test", STRONG)

    def test_email_must_be_unique_across_churches_ignoring_case(self, authenticated_client):
        existing = _other_tenant_user()

        response = authenticated_client.post(
            reverse("user_create"), _new_user_data(email=existing.email.upper())
        )

        assert response.status_code == 200
        assert User.objects.filter(email__iexact=existing.email).count() == 1

    @pytest.mark.parametrize(
        "password1,password2",
        [("12345678", "12345678"), ("corta1", "corta1"), (STRONG, "otra-distinta-77")],
    )
    def test_weak_or_mismatched_password_is_rejected(
        self, authenticated_client, password1, password2
    ):
        response = authenticated_client.post(
            reverse("user_create"), _new_user_data(password1=password1, password2=password2)
        )

        assert response.status_code == 200
        assert not User.objects.filter(email="suhellen@iglesia.test").exists()

    def test_username_collision_gets_a_suffix(self, authenticated_client, admin_user):
        User.objects.create_user(
            email="suhellen@otra.com", password=STRONG, tenant=admin_user.tenant
        )

        authenticated_client.post(reverse("user_create"), _new_user_data())

        assert User.objects.filter(email__in=["suhellen@otra.com", "suhellen@iglesia.test"]).count() == 2


@pytest.mark.django_db
class TestUpdate:
    @pytest.fixture
    def target(self, admin_user):
        return User.objects.create_user(
            email="ana@t.com", password=STRONG, tenant=admin_user.tenant,
            first_name="Ana", last_name="Mora", role="member",
        )

    def test_changes_name_and_role_and_keeps_password_when_blank(
        self, authenticated_client, target
    ):
        response = authenticated_client.post(
            reverse("user_update", args=[target.pk]),
            {"first_name": "Ana María", "last_name": "Mora", "role": "teacher", "is_active": "on"},
        )

        assert response.status_code == 302
        target.refresh_from_db()
        assert (target.first_name, target.role) == ("Ana María", "teacher")
        assert target.can_manage_education
        assert target.check_password(STRONG)

    def test_resets_password(self, authenticated_client, target):
        authenticated_client.post(
            reverse("user_update", args=[target.pk]),
            {
                "first_name": "Ana", "last_name": "Mora", "role": "member", "is_active": "on",
                "password1": "Nueva-Clave-2027", "password2": "Nueva-Clave-2027",
            },
        )

        assert _can_log_in("ana@t.com", "Nueva-Clave-2027")
        assert not _can_log_in("ana@t.com", STRONG)

    def test_unticking_active_blocks_login(self, authenticated_client, target):
        authenticated_client.post(
            reverse("user_update", args=[target.pk]),
            {"first_name": "Ana", "last_name": "Mora", "role": "member"},
        )

        target.refresh_from_db()
        assert not target.is_active
        assert not _can_log_in("ana@t.com", STRONG)

    def test_cannot_touch_other_churches_or_superusers(self, authenticated_client, admin_user):
        foreign = _other_tenant_user()
        root = User.objects.create_user(
            email="root@t.com", password=STRONG, tenant=admin_user.tenant, is_superuser=True
        )
        for victim in (foreign, root):
            url = reverse("user_update", args=[victim.pk])
            assert authenticated_client.get(url).status_code == 404
            assert authenticated_client.post(
                url, {"first_name": "X", "last_name": "Y", "role": "member"}
            ).status_code == 404
            assert authenticated_client.post(
                reverse("user_toggle_active", args=[victim.pk])
            ).status_code == 404

    def test_admin_cannot_demote_or_deactivate_self(self, authenticated_client, admin_user):
        url = reverse("user_update", args=[admin_user.pk])

        page = authenticated_client.get(url)
        assert "password1" not in page.context["form"].fields  # use "Mi perfil" instead

        authenticated_client.post(
            url, {"first_name": "Nuevo", "last_name": "Nombre", "role": "member"}
        )

        admin_user.refresh_from_db()
        assert admin_user.role == "admin" and admin_user.is_active
        assert admin_user.first_name == "Nuevo"  # the name is still editable


@pytest.mark.django_db
class TestToggleActive:
    def test_deactivates_then_reactivates(self, authenticated_client, admin_user):
        target = User.objects.create_user(
            email="b@t.com", password=STRONG, tenant=admin_user.tenant
        )
        url = reverse("user_toggle_active", args=[target.pk])

        authenticated_client.post(url)
        target.refresh_from_db()
        assert not target.is_active and not _can_log_in("b@t.com", STRONG)

        authenticated_client.post(url)
        target.refresh_from_db()
        assert target.is_active and _can_log_in("b@t.com", STRONG)

    def test_cannot_deactivate_self(self, authenticated_client, admin_user):
        authenticated_client.post(reverse("user_toggle_active", args=[admin_user.pk]))

        admin_user.refresh_from_db()
        assert admin_user.is_active

    def test_get_is_not_allowed(self, authenticated_client, admin_user):
        target = User.objects.create_user(
            email="c@t.com", password=STRONG, tenant=admin_user.tenant
        )
        response = authenticated_client.get(reverse("user_toggle_active", args=[target.pk]))
        assert response.status_code == 405


@pytest.mark.django_db
class TestDeactivatedLogin:
    def test_inactive_user_sees_an_explanation_instead_of_a_500(self, admin_user):
        User.objects.create_user(
            email="baja@t.com", password=STRONG, tenant=admin_user.tenant, is_active=False
        )

        response = Client().post(
            reverse("login"), {"login": "baja@t.com", "password": STRONG}, follow=True
        )

        assert response.status_code == 200
        assert "Cuenta desactivada" in response.content.decode()
