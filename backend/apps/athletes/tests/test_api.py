"""API tests for ``/api/v1/athletes/`` (real URLconf, real DB).

Every test is marked ``django_db`` and builds its own data, so the suite
has no order dependencies. Status codes follow the behaviour matrix
verified by @api-builder:

    POST   /api/v1/athletes/         -> 201 / 400
    GET    /api/v1/athletes/{id}/    -> 200 / 404
    GET    /api/v1/athletes/         -> 405 (list not implemented)
    PUT    /api/v1/athletes/{id}/    -> 405
    PATCH  /api/v1/athletes/{id}/    -> 405
    DELETE /api/v1/athletes/{id}/    -> 405
"""

import pytest
from rest_framework import status

from apps.athletes.infrastructure.models import Athlete

LIST_URL = "/api/v1/athletes/"


def detail_url(athlete_id):
    return "/api/v1/athletes/{0}/".format(athlete_id)


# -- POST: create ----------------------------------------------------------


@pytest.mark.django_db
def test_post_valid_athlete_returns_201_and_persists_the_row(api_client, athlete_payload):
    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert body["date_of_birth"] == "2001-03-14"
    assert Athlete.objects.count() == 1


@pytest.mark.django_db
def test_post_then_get_roundtrip_returns_the_same_athlete(api_client, athlete_payload):
    created = api_client.post(LIST_URL, athlete_payload, format="json")
    assert created.status_code == status.HTTP_201_CREATED

    fetched = api_client.get(detail_url(created.json()["id"]))

    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json() == created.json()


@pytest.mark.django_db
def test_post_future_date_of_birth_returns_400_with_field_date_of_birth(api_client, athlete_payload):
    athlete_payload["date_of_birth"] = "2999-01-01"

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["field"] == "date_of_birth"
    assert "detail" in body
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_date_of_birth_before_1900_returns_400(api_client, athlete_payload):
    athlete_payload["date_of_birth"] = "1899-12-31"

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["field"] == "date_of_birth"
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_blank_first_name_returns_400(api_client, athlete_payload):
    athlete_payload["first_name"] = ""

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "first_name" in response.json()
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_whitespace_only_last_name_returns_400(api_client, athlete_payload):
    athlete_payload["last_name"] = "   "

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "last_name" in response.json()
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_missing_fields_returns_400_listing_every_missing_field(api_client):
    response = api_client.post(LIST_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    for field_name in ("first_name", "last_name", "date_of_birth"):
        assert field_name in body, "expected {0} in {1}".format(field_name, body)
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_malformed_date_returns_400(api_client, athlete_payload):
    athlete_payload["date_of_birth"] = "not-a-date"

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "date_of_birth" in response.json()


@pytest.mark.django_db
def test_post_overlong_first_name_returns_400_from_the_orm_translation(api_client, athlete_payload):
    # Only the CharField(max_length=100) rejects this: the serializer
    # and the domain both accept it, so the 400 comes from the
    # repository's ValidationError -> InvalidAthleteData translation.
    athlete_payload["first_name"] = "x" * 101

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["field"] == "first_name"
    assert Athlete.objects.count() == 0


# -- GET: retrieve ---------------------------------------------------------


@pytest.mark.django_db
def test_get_existing_athlete_returns_200(api_client, athlete_row):
    response = api_client.get(detail_url(athlete_row.pk))

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == athlete_row.pk
    assert body["first_name"] == athlete_row.first_name
    assert body["last_name"] == athlete_row.last_name
    assert body["date_of_birth"] == athlete_row.date_of_birth.isoformat()


@pytest.mark.django_db
def test_get_missing_athlete_returns_404_with_detail(api_client):
    response = api_client.get(detail_url(999999))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.django_db
def test_get_non_numeric_pk_returns_404_with_detail(api_client):
    response = api_client.get("/api/v1/athletes/abc/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


# -- unimplemented actions -------------------------------------------------


@pytest.mark.django_db
def test_list_athletes_returns_405(api_client, athlete_row):
    response = api_client.get(LIST_URL)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method",
    ["put", "patch", "delete"],
    ids=["PUT", "PATCH", "DELETE"],
)
def test_mutations_on_detail_return_405(api_client, athlete_row, method):
    response = getattr(api_client, method)(detail_url(athlete_row.pk))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    # Nothing was destroyed by the rejected request.
    assert Athlete.objects.filter(pk=athlete_row.pk).exists()
