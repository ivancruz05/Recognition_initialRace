"""API tests for ``/api/v1/athletes/`` (real URLconf, real DB, JWT).

Every test is marked ``django_db`` and builds its own data, so the suite
has no order dependencies. Status codes follow the RBAC contract of the
monograph (RF-02 / RNF-04):

    unauthenticated          -> 401
    student (any method)     -> 403
    teacher/admin            -> 200 / 201 / 400 / 404 / 405
"""

import pytest
from rest_framework import status

from apps.athletes.infrastructure.models import Athlete

LIST_URL = "/api/v1/athletes/"


def detail_url(athlete_id):
    return "/api/v1/athletes/{0}/".format(athlete_id)


# -- RBAC ------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_list_returns_401(api_client):
    response = api_client.get(LIST_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_student_is_forbidden_on_every_method(api_client, authenticate, athlete_payload, method):
    authenticate(user_type="student")

    if method == "get":
        response = api_client.get(LIST_URL)
    elif method == "post":
        response = api_client.post(LIST_URL, athlete_payload, format="json")
    else:
        response = getattr(api_client, method)(detail_url("ATL-0001"))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_student_cannot_retrieve_an_athlete(api_client, authenticate, athlete_row):
    authenticate(user_type="student")

    response = api_client.get(detail_url(athlete_row.athlete_id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


# -- GET list --------------------------------------------------------------


@pytest.mark.django_db
def test_teacher_list_returns_the_catalogue(api_client, authenticate, athlete_row):
    authenticate(user_type="teacher")

    response = api_client.get(LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert set(body[0]) == {"id", "athlete_id", "label", "group", "registered_at"}
    assert body[0]["athlete_id"] == athlete_row.athlete_id
    assert body[0]["label"] == athlete_row.label
    assert body[0]["registered_at"] == athlete_row.registered_at.isoformat()


@pytest.mark.django_db
def test_admin_list_returns_an_empty_catalogue_without_rows(api_client, authenticate):
    authenticate(user_type="admin")

    response = api_client.get(LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# -- POST create -----------------------------------------------------------


@pytest.mark.django_db
def test_post_valid_athlete_returns_201_and_persists_the_row(
    api_client, authenticate, athlete_payload
):
    authenticate(user_type="teacher")

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["athlete_id"] == "ATL-0001"
    assert body["label"] == "Ada L."
    assert body["group"] == "Grupo 3"
    assert Athlete.objects.count() == 1


@pytest.mark.django_db
def test_post_then_get_roundtrip_returns_the_same_athlete(
    api_client, authenticate, athlete_payload
):
    authenticate(user_type="teacher")
    created = api_client.post(LIST_URL, athlete_payload, format="json")
    assert created.status_code == status.HTTP_201_CREATED

    fetched = api_client.get(detail_url(created.json()["athlete_id"]))

    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json() == created.json()


@pytest.mark.django_db
def test_admin_can_create_athletes(api_client, authenticate, athlete_payload):
    authenticate(user_type="admin")

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_post_missing_athlete_id_returns_400(api_client, authenticate):
    authenticate(user_type="teacher")

    response = api_client.post(LIST_URL, {"label": "Sin codigo"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "athlete_id" in response.json()
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_duplicate_athlete_id_returns_400(
    api_client, authenticate, athlete_payload, athlete_row
):
    authenticate(user_type="teacher")
    athlete_payload["athlete_id"] = athlete_row.athlete_id

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["field"] == "athlete_id"
    assert Athlete.objects.count() == 1


@pytest.mark.django_db
def test_post_blank_label_returns_400(api_client, authenticate, athlete_payload):
    authenticate(user_type="teacher")
    athlete_payload["label"] = "   "

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "label" in response.json()
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_future_registered_at_returns_400_with_the_offending_field(
    api_client, authenticate, athlete_payload
):
    authenticate(user_type="teacher")
    athlete_payload["registered_at"] = "2999-01-01"

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["field"] == "registered_at"
    assert "detail" in body
    assert Athlete.objects.count() == 0


@pytest.mark.django_db
def test_post_malformed_date_returns_400(api_client, authenticate, athlete_payload):
    authenticate(user_type="teacher")
    athlete_payload["registered_at"] = "not-a-date"

    response = api_client.post(LIST_URL, athlete_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "registered_at" in response.json()


@pytest.mark.django_db
def test_post_blank_body_returns_400(api_client, authenticate):
    authenticate(user_type="teacher")

    response = api_client.post(LIST_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "athlete_id" in response.json()
    assert Athlete.objects.count() == 0


# -- GET retrieve ----------------------------------------------------------


@pytest.mark.django_db
def test_get_existing_athlete_returns_200(api_client, authenticate, athlete_row):
    authenticate(user_type="teacher")

    response = api_client.get(detail_url(athlete_row.athlete_id))

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == athlete_row.pk
    assert body["athlete_id"] == athlete_row.athlete_id
    assert body["registered_at"] == athlete_row.registered_at.isoformat()


@pytest.mark.django_db
def test_get_missing_athlete_returns_404_with_detail(api_client, authenticate):
    authenticate(user_type="teacher")

    response = api_client.get(detail_url("ATL-9999"))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.django_db
def test_get_unknown_code_returns_404_with_detail(api_client, authenticate):
    authenticate(user_type="teacher")

    response = api_client.get(detail_url("no-such-code"))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "detail" in response.json()


# -- unimplemented mutations ----------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method",
    ["put", "patch", "delete"],
    ids=["PUT", "PATCH", "DELETE"],
)
def test_mutations_on_detail_return_405(api_client, authenticate, athlete_row, method):
    authenticate(user_type="teacher")

    response = getattr(api_client, method)(detail_url(athlete_row.athlete_id))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    # Nothing was destroyed by the rejected request.
    assert Athlete.objects.filter(pk=athlete_row.pk).exists()
