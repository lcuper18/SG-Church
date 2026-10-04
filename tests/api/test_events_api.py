"""
Integration Tests: Events API
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from events.models import Event, EventRegistration


def _event(tenant, **kwargs):
    kwargs.setdefault("title", "Test Event")
    kwargs.setdefault("start_at", timezone.now() + timedelta(days=3))
    return Event.objects.create(tenant=tenant, **kwargs)


@pytest.mark.integration
@pytest.mark.django_db
class TestEventsAPI:
    def test_list_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/events/")
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_only_own_tenant(self, authenticated_api_client, admin_user, tenant):
        _event(admin_user.tenant, title="Mine")
        _event(tenant, title="Someone else's")

        response = authenticated_api_client.get("/api/v1/events/")

        assert response.status_code == status.HTTP_200_OK
        assert [e["title"] for e in response.data["results"]] == ["Mine"]

    def test_create(self, authenticated_api_client):
        data = {
            "title": "Campamento",
            "event_type": "camp",
            "start_at": (timezone.now() + timedelta(days=10)).isoformat(),
        }
        response = authenticated_api_client.post("/api/v1/events/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_member_role_cannot_create(self, regular_api_client_same_tenant):
        data = {
            "title": "Nope",
            "start_at": (timezone.now() + timedelta(days=1)).isoformat(),
        }
        response = regular_api_client_same_tenant.post(
            "/api/v1/events/", data, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_role_can_list(self, regular_api_client_same_tenant, admin_user):
        _event(admin_user.tenant)
        response = regular_api_client_same_tenant.get("/api/v1/events/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.django_db
class TestEventRegistrationAPI:
    def test_register_member(self, authenticated_api_client, admin_user, member):
        event = _event(admin_user.tenant)
        response = authenticated_api_client.post(
            "/api/v1/event-registrations/", {"member": member.pk, "event": event.pk}
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "registered"

    def test_duplicate_rejected(self, authenticated_api_client, admin_user, member):
        event = _event(admin_user.tenant)
        payload = {"member": member.pk, "event": event.pk}
        authenticated_api_client.post("/api/v1/event-registrations/", payload)
        response = authenticated_api_client.post("/api/v1/event-registrations/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_full_event_rejected(self, authenticated_api_client, admin_user, member):
        event = _event(admin_user.tenant, capacity=0)
        response = authenticated_api_client.post(
            "/api/v1/event-registrations/", {"member": member.pk, "event": event.pk}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_cancels_instead_of_deleting(
        self, authenticated_api_client, admin_user, member
    ):
        event = _event(admin_user.tenant)
        registration = EventRegistration.objects.create(
            tenant=admin_user.tenant, member=member, event=event
        )

        response = authenticated_api_client.delete(
            f"/api/v1/event-registrations/{registration.pk}/"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        registration.refresh_from_db()
        assert registration.status == "cancelled"


@pytest.mark.integration
@pytest.mark.django_db
class TestEventRequirementsAPI:
    def test_baptism_required_blocks_registration(
        self, authenticated_api_client, admin_user, member
    ):
        event = _event(admin_user.tenant, requires_baptized=True)
        response = authenticated_api_client.post(
            "/api/v1/event-registrations/", {"member": member.pk, "event": event.pk}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_baptized_member_can_register(
        self, authenticated_api_client, admin_user, member
    ):
        member.is_baptized = True
        member.save(update_fields=["is_baptized"])
        event = _event(admin_user.tenant, requires_baptized=True)
        response = authenticated_api_client.post(
            "/api/v1/event-registrations/", {"member": member.pk, "event": event.pk}
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_event_with_requirements(self, authenticated_api_client):
        data = {
            "title": "Retiro de parejas",
            "start_at": (timezone.now() + timedelta(days=10)).isoformat(),
            "requires_married": True,
        }
        response = authenticated_api_client.post("/api/v1/events/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["requires_married"] is True
