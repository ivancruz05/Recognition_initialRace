"""Pruebas del adaptador JSON sin base de datos."""

from __future__ import annotations

import json

import pytest

from apps.sessions.domain import AvailabilityStatus, InvalidContractError
from apps.sessions.infrastructure.contract_validator import JsonContractValidator

from .factories import make_contract


def test_validator_acepta_dict_json_y_bytes():
    validator = JsonContractValidator()
    payload = make_contract()
    assert validator.validate(payload).session.session_id == "SES-001"
    assert validator.validate(json.dumps(payload)).session.session_id == "SES-001"
    assert validator.validate(json.dumps(payload).encode("utf-8")).session.session_id == "SES-001"


@pytest.mark.parametrize("raw", ["{bad", b"\xff", [], None])
def test_validator_rechaza_json_malformado_o_payload_no_objeto(raw):
    with pytest.raises(InvalidContractError):
        JsonContractValidator().validate(raw)


def test_validator_nulo_no_se_convierte_en_cero():
    payload = make_contract(metrics={"speed": None})
    metric = JsonContractValidator().validate(payload).session.metrics.speed
    assert metric.status is AvailabilityStatus.NOT_AVAILABLE
    assert metric.value is None
