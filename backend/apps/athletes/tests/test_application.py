"""Unit tests for the athletes application layer (use cases + DTOs).

No Django, no database: the repository port is satisfied by the
in-memory fake defined below, exactly as the use cases expect (they
receive the port through the constructor and know nothing else).
"""

from datetime import date, timedelta

import pytest

from apps.athletes.application import (
    AthleteOutput,
    CreateAthlete,
    CreateAthleteInput,
    GetAthlete,
)
from apps.athletes.domain import (
    Athlete,
    AthleteNotFound,
    AthleteRepository,
    DomainError,
    InvalidAthleteData,
)

VALID_DATE_OF_BIRTH = date(1998, 4, 12)


class InMemoryAthleteRepository(AthleteRepository):
    """Fake ``AthleteRepository``: a dict, no Django, no ORM.

    Assigns sequential ids like a datastore would and raises the real
    domain exceptions so use cases can be tested end to end.
    """

    def __init__(self, start_id=1):
        self._rows = {}
        self._next_id = start_id
        self.added = []
        self.requested_ids = []

    @property
    def rows(self):
        return dict(self._rows)

    def add(self, athlete):
        self.added.append(athlete)
        athlete.id = self._next_id
        self._next_id += 1
        self._rows[athlete.id] = athlete
        return athlete

    def get_by_id(self, athlete_id):
        self.requested_ids.append(athlete_id)
        try:
            return self._rows[athlete_id]
        except KeyError:
            raise AthleteNotFound(athlete_id)


class UnpersistedRepository(InMemoryAthleteRepository):
    """Broken port implementation: never assigns an id (contract breach)."""

    def add(self, athlete):
        self.added.append(athlete)
        return athlete


def valid_input(**overrides):
    payload = {
        "first_name": "Usain",
        "last_name": "Bolt",
        "date_of_birth": VALID_DATE_OF_BIRTH,
    }
    payload.update(overrides)
    return CreateAthleteInput(**payload)


# -- CreateAthlete ---------------------------------------------------------


def test_create_athlete_returns_output_with_assigned_id():
    repository = InMemoryAthleteRepository()
    use_case = CreateAthlete(repository)

    output = use_case.execute(valid_input())

    assert isinstance(output, AthleteOutput)
    assert output.id == 1
    assert output.first_name == "Usain"
    assert output.last_name == "Bolt"
    assert output.date_of_birth == VALID_DATE_OF_BIRTH


def test_create_athlete_persists_exactly_one_record():
    repository = InMemoryAthleteRepository()
    use_case = CreateAthlete(repository)

    use_case.execute(valid_input())

    assert len(repository.rows) == 1
    stored = repository.rows[1]
    assert stored.first_name == "Usain"
    assert stored.id == 1


def test_create_athlete_assigns_sequential_ids():
    repository = InMemoryAthleteRepository()
    use_case = CreateAthlete(repository)

    first = use_case.execute(valid_input())
    second = use_case.execute(valid_input(first_name="Yohan"))

    assert (first.id, second.id) == (1, 2)


def test_create_athlete_propagates_future_date_without_persisting():
    repository = InMemoryAthleteRepository()
    use_case = CreateAthlete(repository)
    invalid = valid_input(date_of_birth=date.today() + timedelta(days=1))

    with pytest.raises(InvalidAthleteData) as exc_info:
        use_case.execute(invalid)

    assert exc_info.value.field == "date_of_birth"
    assert repository.added == []
    assert repository.rows == {}


def test_create_athlete_propagates_blank_first_name():
    repository = InMemoryAthleteRepository()
    use_case = CreateAthlete(repository)

    with pytest.raises(InvalidAthleteData) as exc_info:
        use_case.execute(valid_input(first_name="   "))

    assert exc_info.value.field == "first_name"
    assert repository.rows == {}


def test_create_athlete_uses_the_injected_repository_only():
    repository_a = InMemoryAthleteRepository(start_id=100)
    repository_b = InMemoryAthleteRepository(start_id=500)

    output_a = CreateAthlete(repository_a).execute(valid_input())
    output_b = CreateAthlete(repository_b).execute(valid_input())

    # Independent stores: each use case talks to its own repository.
    assert output_a.id == 100
    assert output_b.id == 500
    assert repository_a.rows.keys() == {100}
    assert repository_b.rows.keys() == {500}
    assert set(repository_a.rows) != set(repository_b.rows)


def test_create_athlete_fails_when_repository_returns_unpersisted_entity():
    # Contract breach by the port: ``id is None`` must surface as a
    # DomainError instead of a half-built output DTO.
    use_case = CreateAthlete(UnpersistedRepository())

    with pytest.raises(DomainError):
        use_case.execute(valid_input())


# -- GetAthlete ------------------------------------------------------------


def test_get_athlete_returns_the_stored_output():
    repository = InMemoryAthleteRepository()
    created = CreateAthlete(repository).execute(valid_input())

    output = GetAthlete(repository).execute(created.id)

    assert output == created
    assert repository.requested_ids == [created.id]


def test_get_athlete_propagates_not_found_with_athlete_id():
    repository = InMemoryAthleteRepository()
    use_case = GetAthlete(repository)

    with pytest.raises(AthleteNotFound) as exc_info:
        use_case.execute(999)

    assert exc_info.value.athlete_id == 999
    assert repository.requested_ids == [999]


def test_get_athlete_uses_its_own_repository_instance():
    populated = InMemoryAthleteRepository()
    empty = InMemoryAthleteRepository()
    CreateAthlete(populated).execute(valid_input())

    output = GetAthlete(populated).execute(1)

    assert output.id == 1
    with pytest.raises(AthleteNotFound) as exc_info:
        GetAthlete(empty).execute(1)
    assert exc_info.value.athlete_id == 1


# -- DTOs ------------------------------------------------------------------


def test_athlete_output_from_entity_requires_an_assigned_id():
    unpersisted = Athlete(
        first_name="Ada",
        last_name="Lovelace",
        date_of_birth=date(1990, 1, 1),
    )

    with pytest.raises(DomainError) as exc_info:
        AthleteOutput.from_entity(unpersisted)

    assert exc_info.value is not None


def test_create_athlete_input_is_frozen():
    data = valid_input()

    with pytest.raises(Exception) as exc_info:
        data.first_name = "changed"

    assert type(exc_info.value).__name__ == "FrozenInstanceError"
