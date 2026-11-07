"""Rule-based recommendation adapter (driven adapter).

Implements ``RecommendationPort`` with documented, conservative rules.
Each output states the pattern observed, the evidence used, the origin
records and the interpretation limits (RF-13 / RF-14 / RNF-10): it never
formulates a clinical or causal conclusion, and it reports
``INSUFFICIENT_DATA`` instead of an unsupported suggestion (CP-11/CP-12).

Rules
-----
R-00  No variable available in any selected session → no recommendation.
R-01  A variable is absent in at least one selected session → explicit
      "No disponible" so a missing value is never read as zero (RF-09).
R-02  Speed: descriptive variation between the first and last session
      with an available value (≥ 2 sessions).
R-03  Stride: same as R-02.
R-04  Cadence: same as R-02.
R-05  Posture: the origin value is reported as-is (no recalculation,
      no grading, RF-05).
"""

from __future__ import annotations

from typing import Sequence

from apps.sessions.domain import SprintSession

from ..domain import (
    Recommendation,
    RecommendationPort,
    RecommendationStatus,
    ReviewState,
)

__all__ = ["RuleBasedRecommendationAdapter"]

VARIABLE_LABELS = {
    "speed": "velocidad",
    "stride": "zancada",
    "cadence": "cadencia",
    "posture": "postura",
}


def _metric(session: SprintSession, name: str):
    return {
        "posture": session.metrics.posture,
        "speed": session.metrics.speed,
        "stride": session.metrics.stride,
        "cadence": session.metrics.cadence,
    }[name]


def _has_any_data(session: SprintSession) -> bool:
    return bool(session.available_variables)


class RuleBasedRecommendationAdapter(RecommendationPort):
    """Documented rule set; deterministic and side-effect free."""

    def generate(self, sessions: Sequence[SprintSession]) -> list[Recommendation]:
        sessions = list(sessions)
        if not sessions or not any(_has_any_data(session) for session in sessions):
            return [
                Recommendation.insufficient_data(
                    recommendation_id="REC-R-00-01",
                    session_ids=[session.session_id for session in sessions],
                    reason=(
                        "ninguna de las sesiones consultadas declara valores de "
                        "postura, velocidad, zancada o cadencia en la fuente"
                    ),
                )
            ]

        recommendations: list[Recommendation] = []
        counter = {"n": 0}

        def next_id(rule_id: str) -> str:
            counter["n"] += 1
            return "REC-{0}-{1:02d}".format(rule_id, counter["n"])

        # R-01 — datos ausentes explícitos --------------------------------
        total = len(sessions)
        for name in ("posture", "speed", "stride", "cadence"):
            missing = [
                session for session in sessions if not _metric(session, name).is_available
            ]
            if not missing:
                continue
            recommendations.append(
                Recommendation(
                    recommendation_id=next_id("R-01"),
                    rule_id="R-01",
                    message=(
                        "Dato no disponible: {0} no está declarada en {1} de {2} "
                        "sesiones consultadas; no se evalúa ni se sustituye por "
                        "cero.".format(VARIABLE_LABELS[name], len(missing), total)
                    ),
                    evidence=(
                        "{0}: ausente en {1}".format(
                            VARIABLE_LABELS[name],
                            ", ".join(session.session_id for session in missing),
                        ),
                    ),
                    session_ids=tuple(session.session_id for session in missing),
                )
            )

        # R-02 / R-03 / R-04 — variación descriptiva entre sesiones -------
        for rule_id, name in (("R-02", "speed"), ("R-03", "stride"), ("R-04", "cadence")):
            available = [
                (session, _metric(session, name))
                for session in sessions
                if _metric(session, name).is_available
                and _metric(session, name).value is not None
            ]
            if len(available) < 2:
                continue
            (first_session, first), (last_session, last) = available[0], available[-1]
            delta = round(last.value - first.value, 3)
            sign = "+" if delta >= 0 else ""
            recommendations.append(
                Recommendation(
                    recommendation_id=next_id(rule_id),
                    rule_id=rule_id,
                    message=(
                        "En las sesiones consultadas la {0} media pasó de {1} a {2} "
                        "{3} (Δ = {4}{5} {3}) entre {6} y {7}. Es una variación "
                        "descriptiva entre registros: puede deberse a la ejecución, "
                        "a la captura o al entrenamiento y corresponde al docente "
                        "interpretarla.".format(
                            VARIABLE_LABELS[name],
                            first.value,
                            last.value,
                            first.unit,
                            sign,
                            delta,
                            first_session.session_id,
                            last_session.session_id,
                        )
                    ),
                    evidence=(
                        "{0}: {1} {2} -> {3} {2} (Δ {4}{5})".format(
                            VARIABLE_LABELS[name],
                            first.value,
                            first.unit,
                            last.value,
                            sign,
                            delta,
                        ),
                        "Sesiones: {0}, {1}".format(
                            first_session.session_id, last_session.session_id
                        ),
                    ),
                    session_ids=(
                        first_session.session_id,
                        last_session.session_id,
                    ),
                )
            )

        # R-05 — postura tal cual la entregó el origen --------------------
        for session in sessions:
            posture = session.metrics.posture
            if not posture.is_available or posture.value is None:
                continue
            recommendations.append(
                Recommendation(
                    recommendation_id=next_id("R-05"),
                    rule_id="R-05",
                    message=(
                        "Postura registrada en {0}: {1} {2} (parámetro '{3}'). "
                        "Se presenta el valor entregado por la fuente, sin "
                        "recálculo ni calificación.".format(
                            session.session_id,
                            posture.value,
                            posture.unit,
                            posture.parameter,
                        )
                    ),
                    evidence=(
                        "posture: {0} {1} ({2})".format(
                            posture.value, posture.unit, posture.parameter
                        ),
                    ),
                    session_ids=(session.session_id,),
                )
            )

        if not recommendations:
            # Caso límite: solo hay datos de variables no cubiertas por reglas.
            recommendations.append(
                Recommendation(
                    recommendation_id=next_id("R-00"),
                    rule_id="R-00",
                    message=(
                        "No hay datos suficientes para emitir una recomendación "
                        "con las reglas documentadas."
                    ),
                    evidence=("Sin variables evaluables por las reglas R-01…R-05",),
                    session_ids=tuple(session.session_id for session in sessions),
                    status=RecommendationStatus.INSUFFICIENT_DATA,
                    review_state=ReviewState.NOT_REQUIRED,
                )
            )

        return recommendations
