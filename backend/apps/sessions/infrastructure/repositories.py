"""Django ORM implementation of the :class:`SessionRepositoryPort`.

Single point of contact between the pure domain layer and Django: domain
entities go in, ORM rows come out (and the other way round). The
``SessionMapper`` below is the only place where both worlds meet.

Dependency rules (checked by @architecture-reviewer):
    * may import ``..domain`` (entities, port, domain exceptions),
      sibling persistence models (FK resolution) and Django/ORM;
    * must NOT import ``..application`` nor ``..interfaces``.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.athletes.infrastructure.models import Athlete as AthleteModel

from ..domain import (
    AvailabilityStatus,
    BiomechanicalMetrics,
    DomainError,
    InvalidSessionData,
    MetricValue,
    PostureMetric,
    SessionFilters,
    SessionNotFound,
    SessionRepositoryPort,
    SprintSession,
    TrainingSession,
    TrainingSessionRepositoryPort,
    TimeSeriesPoint,
    UNIT_CADENCE,
    UNIT_SPEED,
    UNIT_STRIDE,
)
from .models import (
    BiomechanicalMetricModel,
    SprintSessionModel,
    TrainingSessionModel,
)

__all__ = [
    "DjangoSessionRepository",
    "DjangoTrainingSessionRepository",
    "SessionMapper",
]


def _domain_error(message: str, field: Optional[str]) -> InvalidSessionData:
    """Build the domain error type without leaking Django's exceptions."""
    return InvalidSessionData(message, field=field)


class SessionMapper:
    """Bidirectional ``SprintSession`` ⇄ (``SprintSessionModel``,
    ``BiomechanicalMetricModel``) translation.

    Absent metrics are stored as SQL NULL (never as 0.0) and read back as
    ``AvailabilityStatus.NOT_AVAILABLE`` (RF-09).
    """

    # -- entity -> rows ----------------------------------------------------
    @staticmethod
    def to_model(session: SprintSession) -> SprintSessionModel:
        return SprintSessionModel(
            session_id=session.session_id,
            timestamp=session.timestamp,
            test_type=session.test_type,
            metadata=dict(session.metadata),
            training_session_id=session.training_session_id,
        )

    @staticmethod
    def metric_values(metrics: BiomechanicalMetrics) -> dict:
        posture = metrics.posture
        speed = metrics.speed
        stride = metrics.stride
        cadence = metrics.cadence
        return {
            "posture_data": (
                {
                    "value": posture.value,
                    "unit": posture.unit,
                    "parameter": posture.parameter,
                    "details": dict(posture.details),
                }
                if posture.is_available
                else None
            ),
            "speed_avg": speed.value if speed.is_available else None,
            "speed_max": speed.peak if speed.is_available else None,
            "speed_unit": speed.unit,
            "speed_series": SessionMapper._series_to_json(speed),
            "stride_avg": stride.value if stride.is_available else None,
            "stride_max": stride.peak if stride.is_available else None,
            "stride_unit": stride.unit,
            "stride_series": SessionMapper._series_to_json(stride),
            "cadence_avg": cadence.value if cadence.is_available else None,
            "cadence_unit": cadence.unit,
            "cadence_series": SessionMapper._series_to_json(cadence),
        }

    @staticmethod
    def _series_to_json(metric: MetricValue) -> Optional[list]:
        if not metric.is_available or not metric.series:
            return None
        return [{"t": point.t, "v": point.value} for point in metric.series]

    # -- rows -> entity ----------------------------------------------------
    @classmethod
    def to_entity(
        cls, instance: SprintSessionModel, metric_row: BiomechanicalMetricModel
    ) -> SprintSession:
        athlete_code = instance.athlete.athlete_id
        return SprintSession(
            session_id=instance.session_id,
            athlete_id=athlete_code,
            timestamp=instance.timestamp,
            test_type=instance.test_type,
            metrics=cls._metrics_from_row(metric_row),
            metadata=dict(instance.metadata or {}),
            id=instance.pk,
            training_session_id=instance.training_session_id,
        )

    @classmethod
    def _metrics_from_row(cls, row: BiomechanicalMetricModel) -> BiomechanicalMetrics:
        return BiomechanicalMetrics(
            posture=cls._posture_from_row(row),
            speed=cls._metric_from_row(
                row.speed_avg, row.speed_unit or UNIT_SPEED, row.speed_max, row.speed_series, with_peak=True
            ),
            stride=cls._metric_from_row(
                row.stride_avg, row.stride_unit or UNIT_STRIDE, row.stride_max, row.stride_series, with_peak=True
            ),
            cadence=cls._metric_from_row(
                row.cadence_avg, row.cadence_unit or UNIT_CADENCE, None, row.cadence_series, with_peak=False
            ),
        )

    @staticmethod
    def _posture_from_row(row: BiomechanicalMetricModel) -> PostureMetric:
        raw = row.posture_data
        if not raw:
            return PostureMetric.unavailable()
        details = raw.get("details") or {}
        return PostureMetric(
            value=raw.get("value"),
            unit=raw.get("unit") or "deg",
            parameter=raw.get("parameter") or "posture",
            status=(
                AvailabilityStatus.AVAILABLE
                if raw.get("value") is not None
                else AvailabilityStatus.NOT_AVAILABLE
            ),
            details={key: float(value) for key, value in details.items()},
        )

    @staticmethod
    def _metric_from_row(
        value: Optional[float],
        unit: str,
        peak: Optional[float],
        series_json: Optional[list],
        with_peak: bool,
    ) -> MetricValue:
        if value is None:
            return MetricValue.unavailable(unit)
        points = tuple(
            TimeSeriesPoint(t=float(item["t"]), value=float(item["v"]))
            for item in (series_json or [])
            if isinstance(item, dict) and "t" in item and "v" in item
        )
        return MetricValue(
            value=float(value),
            unit=unit,
            status=AvailabilityStatus.AVAILABLE,
            peak=float(peak) if with_peak and peak is not None else None,
            series=points,
        )


class DjangoSessionRepository(SessionRepositoryPort):
    """Concrete ``SessionRepositoryPort`` backed by the Django ORM."""

    def add(self, session: SprintSession) -> SprintSession:
        instance = SessionMapper.to_model(session)
        try:
            athlete = AthleteModel.objects.get(athlete_id=session.athlete_id)
        except AthleteModel.DoesNotExist:
            raise InvalidSessionData(
                "athlete_id {0!r} must exist before ingesting a session".format(
                    session.athlete_id
                ),
                field="athlete_id",
            )
        instance.athlete = athlete

        try:
            instance.full_clean()
        except ValidationError as exc:
            raise _domain_error(*_field_and_message(exc)) from exc

        try:
            with transaction.atomic():
                instance.save()
                BiomechanicalMetricModel.objects.create(
                    session=instance, **SessionMapper.metric_values(session.metrics)
                )
        except IntegrityError as exc:
            raise InvalidSessionData(
                "session_id {0!r} already exists".format(session.session_id),
                field="session_id",
            ) from exc

        session.id = instance.pk
        return session

    def get_by_id(self, session_id: str) -> SprintSession:
        try:
            instance = SprintSessionModel.objects.select_related(
                "athlete", "metric_row"
            ).get(session_id=session_id)
        except SprintSessionModel.DoesNotExist:
            raise SessionNotFound(session_id)
        return SessionMapper.to_entity(instance, instance.metric_row)

    def list(self, filters: SessionFilters) -> list[SprintSession]:
        queryset = self._queryset(filters)
        results = []
        for instance in queryset:
            results.append(
                SessionMapper.to_entity(instance, _metric_row_of(instance))
            )
        return results

    def count_athletes(self, filters: SessionFilters) -> int:
        return (
            self._queryset(filters)
            .values("athlete_id")
            .distinct()
            .count()
        )

    def exists(self, session_id: str) -> bool:
        return SprintSessionModel.objects.filter(session_id=session_id).exists()

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _queryset(filters: SessionFilters):
        queryset = SprintSessionModel.objects.select_related(
            "athlete"
        ).prefetch_related("metric_row")
        if filters.athlete_id:
            queryset = queryset.filter(athlete__athlete_id=filters.athlete_id)
        if filters.session_id:
            queryset = queryset.filter(session_id=filters.session_id)
        if filters.test_type:
            queryset = queryset.filter(test_type__iexact=filters.test_type)
        if filters.date_from:
            queryset = queryset.filter(timestamp__date__gte=filters.date_from)
        if filters.date_to:
            queryset = queryset.filter(timestamp__date__lte=filters.date_to)
        return queryset.order_by("-timestamp")


class DjangoTrainingSessionRepository(TrainingSessionRepositoryPort):
    """ORM adapter for individual training records and their sprint tests."""

    def add(self, session: TrainingSession) -> TrainingSession:
        athlete = self._athlete(session.athlete_id)
        instance = self._to_model(session)
        instance.athlete = athlete
        try:
            instance.full_clean()
        except ValidationError as exc:
            raise _domain_error(*_field_and_message(exc)) from exc

        try:
            with transaction.atomic():
                instance.save()
                self._sync_sprint_tests(instance, session)
        except IntegrityError as exc:
            raise InvalidSessionData(
                "Could not persist the training session", field="training_session"
            ) from exc

        session.id = instance.pk
        return session

    def get_by_id(self, session_id: int) -> TrainingSession:
        try:
            instance = (
                TrainingSessionModel.objects.select_related("athlete")
                .prefetch_related("sprint_tests")
                .get(pk=session_id)
            )
        except TrainingSessionModel.DoesNotExist:
            raise SessionNotFound(str(session_id))
        return self._to_entity(instance)

    def list(self, athlete_id: Optional[str] = None) -> list[TrainingSession]:
        queryset = TrainingSessionModel.objects.select_related("athlete").prefetch_related(
            "sprint_tests"
        )
        if athlete_id:
            queryset = queryset.filter(athlete__athlete_id=athlete_id)
        return [self._to_entity(instance) for instance in queryset]

    def update(self, session: TrainingSession) -> TrainingSession:
        if session.id is None:
            raise InvalidSessionData(
                "A persisted training session is required for update",
                field="id",
            )
        try:
            instance = TrainingSessionModel.objects.get(pk=session.id)
        except TrainingSessionModel.DoesNotExist:
            raise SessionNotFound(str(session.id))

        instance.athlete = self._athlete(session.athlete_id)
        instance.timestamp = session.timestamp
        instance.duration_minutes = session.duration_minutes
        instance.training_type = session.training_type
        instance.attendance_status = session.attendance_status
        instance.coach = session.coach
        instance.location = session.location
        instance.follow_up_notes = session.follow_up_notes
        try:
            instance.full_clean()
        except ValidationError as exc:
            raise _domain_error(*_field_and_message(exc)) from exc

        try:
            with transaction.atomic():
                instance.save()
                self._sync_sprint_tests(instance, session)
        except IntegrityError as exc:
            raise InvalidSessionData(
                "Could not update the training session",
                field="training_session",
            ) from exc
        return self.get_by_id(instance.pk)

    @staticmethod
    def _athlete(athlete_id: str) -> AthleteModel:
        try:
            return AthleteModel.objects.get(athlete_id=athlete_id)
        except AthleteModel.DoesNotExist:
            raise InvalidSessionData(
                "athlete_id must identify an existing athlete",
                field="athlete_id",
            )

    @staticmethod
    def _sync_sprint_tests(
        instance: TrainingSessionModel, session: TrainingSession
    ) -> None:
        tests = list(
            SprintSessionModel.objects.select_for_update()
            .filter(session_id__in=session.sprint_session_ids)
            .select_related("athlete")
        )
        if len(tests) != len(session.sprint_session_ids):
            raise InvalidSessionData(
                "Every sprint_session_id must identify an existing sprint test",
                field="sprint_session_ids",
            )
        for test in tests:
            if test.athlete_id != instance.athlete_id:
                raise InvalidSessionData(
                    "Sprint tests must belong to the training session athlete",
                    field="sprint_session_ids",
                )
            if (
                test.training_session_id is not None
                and test.training_session_id != instance.pk
            ):
                raise InvalidSessionData(
                    "A sprint test can belong to only one training session",
                    field="sprint_session_ids",
                )

        SprintSessionModel.objects.filter(training_session=instance).update(
            training_session=None
        )
        if tests:
            SprintSessionModel.objects.filter(
                pk__in=[test.pk for test in tests]
            ).update(training_session=instance)

    @staticmethod
    def _to_model(session: TrainingSession) -> TrainingSessionModel:
        return TrainingSessionModel(
            timestamp=session.timestamp,
            duration_minutes=session.duration_minutes,
            training_type=session.training_type,
            attendance_status=session.attendance_status,
            coach=session.coach,
            location=session.location,
            follow_up_notes=session.follow_up_notes,
        )

    @staticmethod
    def _to_entity(instance: TrainingSessionModel) -> TrainingSession:
        return TrainingSession(
            athlete_id=instance.athlete.athlete_id,
            timestamp=instance.timestamp,
            duration_minutes=instance.duration_minutes,
            training_type=instance.training_type,
            attendance_status=instance.attendance_status,
            coach=instance.coach,
            location=instance.location,
            follow_up_notes=instance.follow_up_notes,
            sprint_session_ids=tuple(
                sorted(test.session_id for test in instance.sprint_tests.all())
            ),
            id=instance.pk,
        )


def _metric_row_of(instance: SprintSessionModel) -> BiomechanicalMetricModel:
    """Prefetched metric row (the ingestion path always creates one)."""
    try:
        return instance.metric_row
    except SprintSessionModel.metric_row.RelatedObjectDoesNotExist:  # pragma: no cover
        return BiomechanicalMetricModel(session=instance)


def _field_and_message(exc: ValidationError) -> tuple:
    message_dict = getattr(exc, "message_dict", None)
    if message_dict:
        field = sorted(message_dict)[0]
        return field, "{0}: {1}".format(field, "; ".join(message_dict[field]))
    return None, "; ".join(exc.messages)
