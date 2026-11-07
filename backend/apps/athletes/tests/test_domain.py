"""Unit tests for the pure-Python domain layer of ``apps.athletes``.

No Django import, no database, no mocks: only stdlib + domain objects.
The athlete is identified by the pseudonymous technical code of the
monograph contract (Tabla 8); personal fields do not exist here.
"""

from datetime import date, timedelta

import pytest

from apps.athletes.domain import (
    Athlete,
    AthleteNotFound,
    DomainError,
    InvalidAthleteData,
)

VALID_REGISTERED_AT = date(2020, 5, 10)


def build_athlete(**overrides):
    """Helper: valid athlete, overridable per test (keeps tests short)."""
    payload = {
        "athlete_id": "ATL-0001",
        "registered_at": VALID_REGISTERED_AT,
    }
    payload.update(overrides)
    return Athlete(**payload)


# -- happy path ------------------------------------------------------------


def test_valid_athlete_defaults_to_no_label_group_and_id_none():
    athlete = build_athlete()

    assert athlete.athlete_id == "ATL-0001"
    assert athlete.label is None
    assert athlete.group is None
    assert athlete.id is None


def test_valid_athlete_accepts_optional_text_and_persisted_id():
    athlete = build_athlete(
        label="Ada L.", group="Grupo 3", id=42,
    )

    assert athlete.label == "Ada L."
    assert athlete.group == "Grupo 3"
    assert athlete.id == 42


def test_registered_at_defaults_to_today_when_not_given():
    athlete = Athlete(athlete_id="ATL-0002")

    assert athlete.registered_at == date.today()


# -- athlete_id invariants -------------------------------------------------


@pytest.mark.parametrize("invalid_code", [None, 123, 3.14, True])
def test_non_string_athlete_id_is_rejected_with_field_athlete_id(invalid_code):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(athlete_id=invalid_code)

    assert exc_info.value.field == "athlete_id"
    assert "str" in exc_info.value.message


@pytest.mark.parametrize("invalid_code", ["", "   \t "])
def test_blank_athlete_id_is_rejected_with_field_athlete_id(invalid_code):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(athlete_id=invalid_code)

    assert exc_info.value.field == "athlete_id"
    assert "empty" in exc_info.value.message


def test_overlong_athlete_id_is_rejected():
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(athlete_id="A" * 65)

    assert exc_info.value.field == "athlete_id"
    assert "at most 64" in exc_info.value.message


# -- label / group invariants ----------------------------------------------


@pytest.mark.parametrize("field_name", ["label", "group"])
@pytest.mark.parametrize("invalid_value", ["", "   ", 123])
def test_invalid_optional_text_is_rejected_with_the_offending_field(
    field_name, invalid_value
):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(**{field_name: invalid_value})

    assert exc_info.value.field == field_name


@pytest.mark.parametrize("field_name", ["label", "group"])
def test_overlong_optional_text_is_rejected(field_name):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(**{field_name: "x" * 121})

    assert exc_info.value.field == field_name
    assert "at most 120" in exc_info.value.message


# -- registered_at invariants ----------------------------------------------


def test_future_registered_at_is_rejected():
    tomorrow = date.today() + timedelta(days=1)

    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(registered_at=tomorrow)

    assert exc_info.value.field == "registered_at"
    assert "future" in exc_info.value.message


def test_registered_at_before_1900_is_rejected():
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(registered_at=date(1899, 12, 31))

    assert exc_info.value.field == "registered_at"
    assert "before 1900-01-01" in exc_info.value.message


def test_registered_at_exactly_1900_01_01_is_accepted():
    athlete = build_athlete(registered_at=date(1900, 1, 1))

    assert athlete.registered_at == date(1900, 1, 1)


@pytest.mark.parametrize(
    "invalid_value",
    ["2020-05-10", "10/05/2020", None, True, 20200510],
    ids=["iso-str", "other-str", "none", "bool", "int"],
)
def test_registered_at_must_be_a_real_date_object(invalid_value):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(registered_at=invalid_value)

    assert exc_info.value.field == "registered_at"
    assert "datetime.date" in exc_info.value.message


# -- id invariant ----------------------------------------------------------


@pytest.mark.parametrize(
    "invalid_id",
    [0, -1, "3", True, 2.5],
    ids=["zero", "neg", "str", "bool", "float"],
)
def test_invalid_id_is_rejected_with_field_id(invalid_id):
    with pytest.raises(InvalidAthleteData) as exc_info:
        build_athlete(id=invalid_id)

    assert exc_info.value.field == "id"


# -- exception hierarchy ---------------------------------------------------


def test_invalid_athlete_data_is_a_domain_error_and_keeps_message():
    error = InvalidAthleteData("boom", field="athlete_id")

    assert isinstance(error, DomainError)
    assert error.message == "boom"
    assert error.field == "athlete_id"
    assert str(error) == "boom"


def test_athlete_not_found_keeps_the_requested_code():
    error = AthleteNotFound("ATL-9999")

    assert isinstance(error, DomainError)
    assert error.athlete_id == "ATL-9999"
    assert "ATL-9999" in str(error)


def test_invalid_athlete_data_defaults_field_to_none():
    error = InvalidAthleteData("generic")

    assert error.field is None
