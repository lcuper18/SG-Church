"""
Families: a detail page listing who belongs to them, and choosing the members
from the family form itself (create and edit), not only from each member's form.
"""

import re

import pytest
from django.test import Client
from django.urls import reverse

from members.models import Family, Member, User
from tenants.models import Tenant


def _member(tenant, first, last="Mora", **kwargs):
    return Member.objects.create(tenant=tenant, first_name=first, last_name=last, **kwargs)


@pytest.fixture
def people(admin_user):
    t = admin_user.tenant
    return {n: _member(t, n) for n in ("Ana", "Beto", "Carla", "Dani")}


def _checkbox(html, member):
    match = re.search(rf'<input[^>]*id="member_{member.pk}"[^>]*>', html)
    assert match, f"checkbox for {member.first_name} missing"
    return match.group(0)


def _post(client, url, data=None, **extra):
    payload = {"name": "Familia Mora", **(data or {}), **extra}
    return client.post(url, payload)


@pytest.mark.django_db
class TestDetail:
    def test_lists_members_with_the_head_first(self, authenticated_client, admin_user, people):
        family = Family.objects.create(
            tenant=admin_user.tenant, name="Familia Mora", head_of_family=people["Carla"]
        )
        for m in people.values():
            m.family = family
            m.save()

        response = authenticated_client.get(reverse("family_detail", args=[family.pk]))

        names = [m.first_name for m in response.context["family_members"]]
        assert names[0] == "Carla" and set(names) == set(people)
        html = response.content.decode()
        assert "Cabeza" in html and "Ana Mora" in html and "Dani Mora" in html

    def test_family_without_members_says_so(self, authenticated_client, admin_user):
        family = Family.objects.create(tenant=admin_user.tenant, name="Vacía")

        html = authenticated_client.get(reverse("family_detail", args=[family.pk])).content.decode()

        assert "aún no tiene miembros" in html

    def test_other_churches_and_anonymous_users_are_kept_out(self, authenticated_client):
        foreign = Family.objects.create(
            tenant=Tenant.objects.create(name="O", subdomain="o-fam"), name="Ajena"
        )
        url = reverse("family_detail", args=[foreign.pk])

        assert authenticated_client.get(url).status_code == 404
        assert Client().get(url).status_code == 302

    def test_read_only_roles_can_view_but_not_see_edit_buttons(self, admin_user):
        family = Family.objects.create(tenant=admin_user.tenant, name="Mora")
        viewer = User.objects.create_user(
            email="v@t.com", password="x-Strong-pass-1", role="member", tenant=admin_user.tenant
        )
        client = Client()
        client.force_login(viewer)

        response = client.get(reverse("family_detail", args=[family.pk]))

        assert response.status_code == 200
        assert reverse("family_update", args=[family.pk]) not in response.content.decode()

    def test_list_and_member_pages_link_to_it(self, authenticated_client, admin_user, people):
        family = Family.objects.create(tenant=admin_user.tenant, name="Mora")
        people["Ana"].family = family
        people["Ana"].save()
        url = reverse("family_detail", args=[family.pk])

        assert url in authenticated_client.get(reverse("family_list")).content.decode()
        member_page = authenticated_client.get(reverse("member_detail", args=[people["Ana"].pk]))
        assert url in member_page.content.decode()


@pytest.mark.django_db
class TestCreateWithMembers:
    def test_members_ticked_on_creation_join_the_family(
        self, authenticated_client, admin_user, people
    ):
        response = _post(
            authenticated_client, reverse("family_create"),
            members=[str(people["Ana"].pk), str(people["Beto"].pk)],
        )

        family = Family.objects.get(name="Familia Mora")
        assert response.status_code == 302
        assert response.url == reverse("family_detail", args=[family.pk])
        assert family.tenant == admin_user.tenant
        assert set(family.members.all()) == {people["Ana"], people["Beto"]}

    def test_the_head_is_added_even_if_not_ticked(self, authenticated_client, people):
        _post(
            authenticated_client, reverse("family_create"),
            head_of_family=str(people["Dani"].pk), members=[str(people["Ana"].pk)],
        )

        family = Family.objects.get(name="Familia Mora")
        assert set(family.members.all()) == {people["Ana"], people["Dani"]}

    def test_a_duplicate_name_is_a_form_error_not_a_500(self, authenticated_client, admin_user):
        Family.objects.create(tenant=admin_user.tenant, name="Familia Mora")

        response = _post(authenticated_client, reverse("family_create"), name="familia mora")

        assert response.status_code == 200
        assert "Ya existe una familia" in response.content.decode()
        assert Family.objects.filter(tenant=admin_user.tenant).count() == 1

    def test_the_same_name_in_another_church_is_fine(self, authenticated_client):
        Family.objects.create(tenant=Tenant.objects.create(name="O", subdomain="o-fam2"), name="Familia Mora")

        assert _post(authenticated_client, reverse("family_create")).status_code == 302

    def test_other_churches_members_cannot_be_added(self, authenticated_client):
        stranger = _member(Tenant.objects.create(name="O", subdomain="o-fam3"), "Ajeno")

        response = _post(authenticated_client, reverse("family_create"), members=[str(stranger.pk)])

        assert response.status_code == 200
        stranger.refresh_from_db()
        assert stranger.family is None and not Family.objects.filter(name="Familia Mora").exists()


@pytest.mark.django_db
class TestEditMembers:
    @pytest.fixture
    def family(self, admin_user, people):
        family = Family.objects.create(
            tenant=admin_user.tenant, name="Familia Mora", head_of_family=people["Ana"]
        )
        for name in ("Ana", "Beto"):
            people[name].family = family
            people[name].save()
        return family

    def test_form_shows_current_members_checked(self, authenticated_client, family, people):
        html = authenticated_client.get(reverse("family_update", args=[family.pk])).content.decode()

        assert "checked" in _checkbox(html, people["Ana"])
        assert "checked" in _checkbox(html, people["Beto"])
        assert "checked" not in _checkbox(html, people["Carla"])

    def test_add_and_remove_members(self, authenticated_client, family, people):
        response = _post(
            authenticated_client, reverse("family_update", args=[family.pk]),
            head_of_family=str(people["Ana"].pk),
            members=[str(people["Ana"].pk), str(people["Carla"].pk)],  # Beto unticked
        )

        assert response.status_code == 302
        assert set(family.members.all()) == {people["Ana"], people["Carla"]}
        people["Beto"].refresh_from_db()
        assert people["Beto"].family is None

    def test_unticking_everyone_empties_the_family(self, authenticated_client, family, people):
        _post(authenticated_client, reverse("family_update", args=[family.pk]))

        assert family.members.count() == 0

    def test_someone_in_another_family_is_moved_and_loses_headship_there(
        self, authenticated_client, admin_user, family, people
    ):
        other = Family.objects.create(
            tenant=admin_user.tenant, name="Otra", head_of_family=people["Dani"]
        )
        people["Dani"].family = other
        people["Dani"].save()

        html = authenticated_client.get(reverse("family_update", args=[family.pk])).content.decode()
        assert "ahora en Otra" in html  # warned before moving

        _post(
            authenticated_client, reverse("family_update", args=[family.pk]),
            head_of_family=str(people["Ana"].pk),
            members=[str(people["Ana"].pk), str(people["Dani"].pk)],
        )

        people["Dani"].refresh_from_db()
        other.refresh_from_db()
        assert people["Dani"].family == family
        assert other.head_of_family is None

    def test_failed_validation_keeps_the_ticks(self, authenticated_client, family, people):
        response = _post(
            authenticated_client, reverse("family_update", args=[family.pk]),
            name="", members=[str(people["Dani"].pk)],
        )

        html = response.content.decode()
        assert response.status_code == 200
        assert "checked" in _checkbox(html, people["Dani"])
        assert "checked" not in _checkbox(html, people["Ana"])
        assert family.members.count() == 2  # nothing was saved

    def test_renaming_keeps_its_own_name_valid(self, authenticated_client, family, people):
        response = _post(
            authenticated_client, reverse("family_update", args=[family.pk]),
            members=[str(people["Ana"].pk)],
        )

        assert response.status_code == 302

    @pytest.mark.parametrize("role", ["member", "teacher", "treasurer"])
    def test_roles_that_cannot_manage_members_get_403(self, admin_user, family, role):
        user = User.objects.create_user(
            email=f"{role}@t.com", password="x-Strong-pass-1", role=role, tenant=admin_user.tenant
        )
        client = Client()
        client.force_login(user)

        assert client.get(reverse("family_update", args=[family.pk])).status_code == 403
        assert _post(client, reverse("family_update", args=[family.pk])).status_code == 403
