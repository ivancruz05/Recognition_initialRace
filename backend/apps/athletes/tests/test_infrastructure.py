"""Integration tests for ``DjangoAthleteRepository`` (real DB, real ORM).

Covers the translation points the API matrix does not reach:
``ValidationError`` → ``InvalidAthleteData`` (schema level, incl. a
duplicated technical code) and ``DoesNotExist`` → ``AthleteNotFound``.
"""

from datetime import date

import pytest

from apps.athletes.domain import Athlete, AthleteNotFound, InvalidAthleteData
from apps.athletes.infrastructure.models import Athlete as AthleteModel
from apps.athletes.infrastructure.repositories import DjangoAthleteRepository


@pytest.mark.django_db
def test_add_persists_the_row_and_assigns_the_generated_id():
    repository = DjangoAthleteRepository()

    saved = repository.add(
        Athlete(
            athlete_id="ATL-0001",
            label="Kipchoge E.",
            group="Grupo 2",
            registered_at=date(2020, 5, 10),
        )
    )

    assert saved.id is not None
    assert saved.id > 0
    row = AthleteModel.objects.get(pk=saved.id)
    assert row.athlete_id == "ATL-0001"
    assert row.label == "Kipchoge E."
    assert row.group == "Grupo 2"
    assert row.registered_at == date(2020, 5, 10)


@pytest.mark.django_db
def test_add_translates_duplicated_code_into_invalid_athlete_data():
    # ``athlete_id`` is unique in the schema: only the ORM can reject
    # the second row, so the repository must do the translation.
    repository = DjangoAthleteRepository()
    repository.add(Athlete(athlete_id="ATL-0001"))

    with pytest.raises(InvalidAthleteData) as exc_info:
        repository.add(Athlete(athlete_id="ATL-0001"))

    assert exc_info.value.field == "athlete_id"
    assert AthleteModel.objects.count() == 1


@pytest.mark.django_db
def test_get_by_athlete_id_returns_the_persisted_entity():
    repository = DjangoAthleteRepository()
    repository.add(
        Athlete(
            athlete_id="ATL-0007",
            label="Bubka S.",
            registered_at=date(1963, 12, 4),
        )
    )

    loaded = repository.get_by_athlete_id("ATL-0007")

    assert loaded.athlete_id == "ATL-0007"
    assert loaded.label == "Bubka S."
    assert loaded.registered_at == date(1963, 12, 4)
    assert isinstance(loaded, Athlete)
    assert loaded.id is not None


@pytest.mark.django_db
def test_get_by_athlete_id_raises_athlete_not_found_with_the_requested_code():
    repository = DjangoAthleteRepository()

    with pytest.raises(AthleteNotFound) as exc_info:
        repository.get_by_athlete_id("ATL-9999")

    assert exc_info.value.athlete_id == "ATL-9999"


@pytest.mark.django_db
def test_list_all_returns_every_row_ordered_by_code():
    repository = DjangoAthleteRepository()
    repository.add(Athlete(athlete_id="ATL-0010"))
    repository.add(Athlete(athlete_id="ATL-0002"))
    repository.add(Athlete(athlete_id="ATL-0007"))

    codes = [athlete.athlete_id for athlete in repository.list_all()]

    assert codes == ["ATL-0002", "ATL-0007", "ATL-0010"]


@pytest.mark.django_db
def test_optional_text_stays_null_when_not_provided():
    repository = DjangoAthleteRepository()

    saved = repository.add(Athlete(athlete_id="ATL-0003"))
    loaded = repository.get_by_athlete_id(saved.athlete_id)

    assert loaded.label is None
    assert loaded.group is None
