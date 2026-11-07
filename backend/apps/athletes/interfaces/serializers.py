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
    ``athlete_id`` (obligatorio) y ``label`` / ``group`` /
    ``registered_at`` (opcionales).
    Outbound (``to_representation``): an ``AthleteOutput`` DTO.
    """

    id = serializers.IntegerField(read_only=True)
    athlete_id = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=False,
        trim_whitespace=True,
        max_length=64,
    )
    label = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        max_length=120,
        default=None,
    )
    group = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        max_length=120,
        default=None,
    )
    registered_at = serializers.DateField(required=False, allow_null=True, default=None)

    # -- mapping helpers ---------------------------------------------------
    def to_application_input(self, validated_data: dict) -> CreateAthleteInput:
        """Map the validated payload to the application input DTO.

        ``DateField`` already returns a ``datetime.date`` after
        validation; the ``str`` branch is defensive input handling in
        case the payload reaches this method unvalidated.
        """
        registered_at = validated_data.get("registered_at")
        if isinstance(registered_at, str):
            registered_at = datetime.strptime(registered_at, "%Y-%m-%d").date()
        return CreateAthleteInput(
            athlete_id=validated_data["athlete_id"],
            label=validated_data.get("label"),
            group=validated_data.get("group"),
            registered_at=registered_at,
        )

    def to_representation(self, output: AthleteOutput) -> dict:
        """Map the application output DTO to a JSON-ready dict.

        Overridden on purpose: this serializer always renders an
        ``AthleteOutput`` (the domain entity never reaches this layer),
        so ``registered_at`` is serialized with an explicit
        ``YYYY-MM-DD`` format.
        """
        return {
            "id": output.id,
            "athlete_id": output.athlete_id,
            "label": output.label,
            "group": output.group,
            "registered_at": output.registered_at.isoformat()
            if isinstance(output.registered_at, date)
            else output.registered_at,
        }
