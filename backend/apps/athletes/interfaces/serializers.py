"""DRF serializers for the athletes module.

The serializer validates the *shape and type* of the incoming payload
and maps it to and from application DTOs. Business truth stays in
``domain/``: everything this serializer accepts may still be rejected by
the domain (the use case raises ``InvalidAthleteData``, translated to
HTTP 400 by the view).

Dependency rules (checked by @architecture-reviewer):
    * may import ``rest_framework`` and ``..application`` (DTOs only);
    * must NOT import ``..domain`` nor ``..infrastructure``.
"""

from __future__ import annotations

from datetime import date, datetime

from rest_framework import serializers

from ..application import AthleteOutput, CreateAthleteInput

__all__ = ["AthleteSerializer"]


class AthleteSerializer(serializers.Serializer):
    """Validate a create-athlete payload / render an ``AthleteOutput``.

    Inbound (``is_valid`` → ``to_application_input``): JSON body with
    ``first_name``, ``last_name`` and ``date_of_birth``.
    Outbound (``to_representation``): an ``AthleteOutput`` DTO.
    """

    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        trim_whitespace=True,
    )
    last_name = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        trim_whitespace=True,
    )
    date_of_birth = serializers.DateField(required=True)

    # -- shape-level validation (not business rules) ----------------------
    def validate_first_name(self, value: str) -> str:
        """Reject empty / whitespace-only ``first_name``.

        Mirrors nothing but the input shape: the domain keeps the final
        say (it may reject other values the serializer accepts).
        """
        if not value.strip():
            raise serializers.ValidationError("first_name must not be empty.")
        return value

    def validate_last_name(self, value: str) -> str:
        """Reject empty / whitespace-only ``last_name``."""
        if not value.strip():
            raise serializers.ValidationError("last_name must not be empty.")
        return value

    # -- mapping helpers ---------------------------------------------------
    def to_application_input(self, validated_data: dict) -> CreateAthleteInput:
        """Map the validated payload to the application input DTO.

        Args:
            validated_data: result of a successful ``is_valid()`` call.

        Returns:
            A frozen :class:`CreateAthleteInput` ready for the
            ``CreateAthlete`` use case.

        ``DateField`` already returns a ``datetime.date`` after
        validation; the ``str`` branch is defensive input handling in
        case the payload reaches this method unvalidated.
        """
        date_of_birth = validated_data["date_of_birth"]
        if isinstance(date_of_birth, str):
            date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        if not isinstance(date_of_birth, date):  # pragma: no cover - defensive
            raise serializers.ValidationError(
                {"date_of_birth": "Expected a date in YYYY-MM-DD format."}
            )
        return CreateAthleteInput(
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            date_of_birth=date_of_birth,
        )

    def to_representation(self, output: AthleteOutput) -> dict:
        """Map the application output DTO to a JSON-ready dict.

        Overridden on purpose: this serializer always renders an
        ``AthleteOutput`` (the domain entity never reaches this layer),
        so ``date_of_birth`` is serialized from its ``datetime.date``
        value with an explicit ``YYYY-MM-DD`` format.
        """
        return {
            "id": output.id,
            "first_name": output.first_name,
            "last_name": output.last_name,
            "date_of_birth": output.date_of_birth.isoformat(),
        }
