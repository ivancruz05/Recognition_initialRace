"""Unit tests for the pure-Python domain layer of ``apps.athletes``.

No Django import, no database, no mocks: only stdlib + domain objects.
"""

from datetime import date, timedelta

import pytest

from apps.athletes.domain import (
    Athlete,
    AthleteNotFound,
    DomainError,
    InvalidAthleteData,
)

VALID_DATE_OF_BIRTH = date(2000, 6, 15)


def build_athlete(**overrides):
    """Helper: valid athlete, overridable per test (keeps tests short)."""
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "date_of_birth": VALID_DATE_OF_BIRTH,
    }
    payload.update(overrides)
    return Athlete(**payload)


# -- happy path ------------------------------------------------------------


def test_valid_athlete_is_created_with_default_id_none():
    athlete = build_athlete()

    assert athlete.first_name == "Ada"
    assert athlete.last_name == "Lovelace"
    assert athlete.date_of_birth == VALID_DATE_OF_BIRTH
    assert athlete.id is None


def test_valid_athlete_accepts_persisted_positive_id():
    athlete = build_athlete(id=42)

    assert athlete.id == 42


def test_valid_athlete_keeps_surrounding_whitespace_in_names():
    # The domain only *validates* (``value.strip()`` non-empty); it does
    # not rewrite the attribute.
    athlete = build_athlete(first_name="  Ada  ")

    assert athlete.first_name == "  Ada  "
    assert athlete.id is None


# -- name invariants -------------------------------------------------------


@pytest.mark.parametrize("field_name", ["first_name", "last_name"])
def test_blank_name_is_rejected_with_the_offending_field(field_name):
    overrides = {field_name: ""}

    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(**overrides)

    assert exc_info.value.field == field_name
    assert "empty" in exc_info.value.message


@pytest.mark.parametrize("field_name", ["first_name", "last_name"])
def test_whitespace_only_name_is_rejected_with_the_offending_field(field_name):
    overrides = {field_name: "   \t "}

    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(**overrides)

    assert exc_info.value.field == field_name
    assert "empty" in exc_info.value.message


@pytest.mark.parametrize("field_name", ["first_name", "last_name"])
def test_non_string_name_is_rejected_with_the_offending_field(field_name):
    overrides = {field_name: 123}

    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(**overrides)

    assert exc_info.value.field == field_name
    assert "str" in exc_info.value.message


# -- date_of_birth invariants ----------------------------------------------


def test_future_date_of_birth_is_rejected():
    tomorrow = date.today() + timedelta(days=1)

    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(date_of_birth=tomorrow)

    assert exc_info.value.field == "date_of_birth"
    assert "future" in exc_info.value.message


def test_date_of_birth_before_1900_is_rejected():
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(date_of_birth=date(1899, 12, 31))

    assert exc_info.value.field == "date_of_birth"
    assert "before 1900-01-01" in exc_info.value.message


def test_date_of_birth_exactly_1900_01_01_is_accepted():
    athlete = build_athlete(date_of_birth=date(1900, 1, 1))

    assert athlete.date_of_birth == date(1900, 1, 1)


@pytest.mark.parametrize(
    "invalid_value",
    ["2000-01-01", "15/06/2000", None, True, 20000101],
    ids=["iso-str", "other-str", "none", "bool", "int"],
)
def test_date_of_birth_must_be_a_real_date_object(invalid_value):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(date_of_birth=invalid_value)

    assert exc_info.value.field == "date_of_birth"
    assert "datetime.date" in exc_info.value.message


# -- id invariant ----------------------------------------------------------


@pytest.mark.parametrize("invalid_id", [0, -1, "3", True, 2.5], ids=["zero", "neg", "str", "bool", "float"])
def test_invalid_id_is_rejected_with_field_id(invalid_id):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(id=invalid_id)

    assert exc_info.value.field == "id"


# -- exception hierarchy ---------------------------------------------------


def test_invalid_athlete_data_is_a_domain_error_and_keeps_message():
    error = InvalidAthleteData("boom", field="first_name")

    assert isinstance(error, DomainError)
    assert error.message == "boom"
    assert error.field == "first_name"
    assert str(error) == "boom"


def test_athlete_not_found_keeps_athlete_id():
    error = AthleteNotFound(7)

    assert isinstance(error, DomainError)
    assert error.athlete_id == 7
    assert "7" in str(error)


def test_invalid_athlete_data_defaults_field_to_none():
    error = InvalidAthleteData("generic")

    assert error.field is None
