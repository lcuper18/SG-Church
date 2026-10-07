"""
The member form must let staff pick tags. The view always accepted `tags`, but
the hand-written template had no field for it, so tags could not be assigned
from the UI at all.
"""

import re

import pytest

from members.models import Member, Tag
from tenants.models import Tenant

BASE = {"first_name": "Ana", "last_name": "Mora", "member_status": "member"}


def _checkbox(html, tag):
    match = re.search(rf'<input[^>]*id="tag_{tag.pk}"[^>]*>', html)
    assert match, f"checkbox for tag {tag.name} not rendered"
    return match.group(0)


@pytest.fixture
def tags(admin_user):
    return [
        Tag.objects.create(tenant=admin_user.tenant, name="Jóvenes", color="#10B981"),
        Tag.objects.create(tenant=admin_user.tenant, name="Música", color="#F59E0B"),
    ]


@pytest.mark.django_db
class TestMemberTagsForm:
    def test_create_form_lists_only_this_churchs_tags(
        self, authenticated_client, tags
    ):
        other = Tag.objects.create(
            tenant=Tenant.objects.create(name="Otra", subdomain="otra-tags"),
            name="Ajena",
        )
        html = authenticated_client.get("/members/create/").content.decode()

        for tag in tags:
            assert "checked" not in _checkbox(html, tag)
        assert f'id="tag_{other.pk}"' not in html

    def test_create_member_with_tags(self, authenticated_client, admin_user, tags):
        response = authenticated_client.post(
            "/members/create/", {**BASE, "tags": [str(t.pk) for t in tags]}
        )

        assert response.status_code == 302
        member = Member.objects.get(first_name="Ana", tenant=admin_user.tenant)
        assert set(member.tags.all()) == set(tags)

    def test_edit_form_checks_current_tags_and_can_change_them(
        self, authenticated_client, admin_user, tags
    ):
        member = Member.objects.create(tenant=admin_user.tenant, **BASE)
        member.tags.add(tags[0])

        html = authenticated_client.get(f"/members/{member.pk}/edit/").content.decode()
        assert "checked" in _checkbox(html, tags[0])
        assert "checked" not in _checkbox(html, tags[1])

        authenticated_client.post(
            f"/members/{member.pk}/edit/", {**BASE, "tags": [str(tags[1].pk)]}
        )
        assert list(member.tags.all()) == [tags[1]]

    def test_unticking_every_tag_clears_them(self, authenticated_client, admin_user, tags):
        member = Member.objects.create(tenant=admin_user.tenant, **BASE)
        member.tags.add(*tags)

        authenticated_client.post(f"/members/{member.pk}/edit/", BASE)

        assert member.tags.count() == 0

    def test_other_churchs_tag_is_rejected(self, authenticated_client, admin_user):
        foreign = Tag.objects.create(
            tenant=Tenant.objects.create(name="Otra", subdomain="otra-tags2"),
            name="Ajena",
        )

        response = authenticated_client.post(
            "/members/create/", {**BASE, "tags": [str(foreign.pk)]}
        )

        assert response.status_code == 200  # form re-rendered with an error
        assert not Member.objects.filter(first_name="Ana").exists()

    def test_ticked_tags_survive_a_failed_validation(
        self, authenticated_client, tags
    ):
        # Missing first_name -> invalid; the ticked tag must stay ticked.
        response = authenticated_client.post(
            "/members/create/",
            {"last_name": "Mora", "member_status": "member", "tags": [str(tags[1].pk)]},
        )

        html = response.content.decode()
        assert response.status_code == 200
        assert "checked" in _checkbox(html, tags[1])
        assert "checked" not in _checkbox(html, tags[0])
