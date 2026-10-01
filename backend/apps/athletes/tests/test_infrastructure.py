"""Integration tests for ``DjangoAthleteRepository`` (real DB, real ORM).

Covers the translation points the API matrix does not reach:
``ValidationError`` → ``InvalidAthleteData`` (schema level) and
``DoesNotExist`` → ``AthleteNotFound``.
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
            first_name="Kipchoge",
            last_name="Eliud",
            date_of_birth=date(1984, 11, 10),
        )
    )

    assert saved.id is not None
    assert saved.id > 0
    row = AthleteModel.objects.get(pk=saved.id)
    assert row.first_name == "Kipchoge"
    assert row.date_of_birth == date(1984, 11, 10)


@pytest.mark.django_db
def test_add_translates_django_validation_error_into_invalid_athlete_data():
    # Longer than the model's CharField(max_length=100): only the ORM
    # can reject this, so the repository must do the translation.
    repository = DjangoAthleteRepository()
    athlete = Athlete(
        first_name="x" * 101,
        last_name="Valid",
        date_of_birth=date(1990, 1, 1),
    )

    with pytest.raises(InvalidAthleteData) as exc_info:
        repository.add(athlete)

    assert exc_info.value.field == "first_name"
    assert AthleteModel.objects.count() == 0


@pytest.mark.django_db
def test_get_by_id_returns_the_persisted_entity():
    repository = DjangoAthleteRepository()
    saved = repository.add(
        Athlete(
            first_name="Bubka",
            last_name="Sergey",
            date_of_birth=date(1963, 12, 4),
        )
    )

    loaded = repository.get_by_id(saved.id)

    assert loaded.id == saved.id
    assert loaded.first_name == "Bubka"
    assert loaded.last_name == "Sergey"
    assert loaded.date_of_birth == date(1963, 12, 4)
    assert isinstance(loaded, Athlete)


@pytest.mark.django_db
def test_get_by_id_raises_athlete_not_found_with_the_requested_id():
    repository = DjangoAthleteRepository()

    with pytest.raises(AthleteNotFound) as exc_info:
        repository.get_by_id(424242)

    assert exc_info.value.athlete_id == 424242
