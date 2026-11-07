"""JSON contract validator (outbound adapter).

Translates transport concerns (bytes/str decoding) and delegates every
business rule to the pure domain function ``build_session``. Swapping
this adapter for a CSV/XML one does not touch the domain nor the use
cases (RNF-01, HU-07).
"""

from __future__ import annotations

import json
from typing import Any

from ..domain import ContractValidatorPort, InvalidContractError, ValidatedContract, build_session

__all__ = ["JsonContractValidator"]


class JsonContractValidator(ContractValidatorPort):
    """``ContractValidatorPort`` backed by JSON payloads."""

    def validate(self, raw: Any) -> ValidatedContract:
        """Decode (when needed) and validate ``raw`` against the contract.

        Raises:
            InvalidContractError: for malformed JSON *and* for any rule
                of the data contract; the caller persists nothing.
        """
        payload = raw
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError:
                raise InvalidContractError.single(
                    "payload", "must be UTF-8 encoded JSON"
                )
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise InvalidContractError.single(
                    "payload", "malformed JSON ({0})".format(exc.msg)
                )
        return build_session(payload)
