"""Fase I CSV export adapter (driven adapter).

Reads the versioned export produced by the Fase I project
(``data_export/csv/*.csv``, see ``data_export/README.md``) and maps it to
minimum-contract payloads (monograph Tabla 8) plus a data-quality
profile (RF-11 / RNF-09 / CP-08).

Mapping rules (Cap. 7.3, "Tabla de mapeo entre la Fase I y el contrato"):

* ``athletes.id`` → pseudonymous ``athlete_id`` (``ATL-0001``). Personal
  fields of the source (names, identification, e-mail) are NOT imported.
* ``analyses`` (status COMPLETED) → one sprint session each, keyed
  ``SES-F1-<analysis id>``; only tests of 10 m are mapped, the rest are
  reported as skipped (no evidence for other distances).
* ``metrics`` → ``speed`` / ``stride`` / ``cadence`` / ``posture`` with
  the units declared by the source; a NULL source value becomes
  ``NOT_AVAILABLE``, never 0.
* ``frame_metrics`` → the optional speed series, trimmed to the
  displacement span (first→last frame with speed > 0). The trimming is
  documented in ``metadata.observation`` and counted in the profile.

Pure Python (stdlib only): no Django, so it can run inside tests and
management commands alike.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

__all__ = ["Fase1ExportAdapter", "Fase1Batch"]

SOURCE_SYSTEM = "Athletic_Export_FaseI"
SCHEMA_VERSION = "1.0.0"
TEST_DISTANCE_METERS = 10
# Velocidad mundial ~12.4 m/s: por encima de 12 m/s el dato se marca como
# atípico en el perfil (no se elimina: se renderiza tal cual lo entregó el origen).
SPEED_OUTLIER_THRESHOLD = 12.0

UNIT_SPEED = "m/s"
UNIT_STRIDE = "m"
UNIT_CADENCE = "pasos/s"
UNIT_POSTURE = "score"  # la fuente declara un "score", no un ángulo en grados


@dataclass
class Fase1Batch:
    """Contract payloads ready to ingest + the quality profile."""

    payloads: list = field(default_factory=list)
    profile: dict = field(default_factory=dict)


class Fase1ExportAdapter:
    """Maps ``data_export/csv`` (Fase I) to minimum-contract payloads."""

    def __init__(self, csv_dir) -> None:
        self.csv_dir = Path(csv_dir)

    # -- public API --------------------------------------------------------
    def load(self) -> Fase1Batch:
        # Index the relational tables by their technical id: analyses →
        # videos → tests → athletes is how the export links them.
        athletes = {row["id"]: row for row in self._load("athletes")}
        tests = {row["id"]: row for row in self._load("tests")}
        videos = {row["id"]: row for row in self._load("videos")}
        analyses = self._load("analyses")
        metrics = {row["analysis_id"]: row for row in self._load("metrics")}
        frames = defaultdict(list)
        for row in self._load("frame_metrics"):
            frames[row["analysis_id"]].append(row)

        payloads, skipped, missing, zeros = [], [], defaultdict(int), defaultdict(int)
        speed_values, frames_total, frames_trimmed = [], 0, 0

        for analysis in analyses:
            if analysis.get("status") != "COMPLETED":
                skipped.append(
                    {"session_id": _session_id(analysis), "reason": "analysis not completed"}
                )
                continue

            video = videos.get(analysis.get("video_id"))
            test = tests.get(video.get("test_id")) if video else None
            if test is None:
                skipped.append(
                    {"session_id": _session_id(analysis), "reason": "no source test/video"}
                )
                continue
            if str(test.get("distance", "")).strip() != str(TEST_DISTANCE_METERS):
                skipped.append(
                    {
                        "session_id": _session_id(analysis),
                        "reason": "distance {0} m is out of scope (only {1} m)".format(
                            test.get("distance"), TEST_DISTANCE_METERS
                        ),
                    }
                )
                continue

            metric = metrics.get(analysis["id"])
            if metric is None:
                skipped.append(
                    {"session_id": _session_id(analysis), "reason": "no metrics row"}
                )
                continue

            frame_rows = sorted(
                frames.get(analysis["id"], []),
                key=lambda row: _number(row.get("frame_number")),
            )
            series, trimmed = _speed_series(frame_rows)
            frames_total += len(frame_rows)
            frames_trimmed += trimmed

            speed_avg = _number_or_none(metric.get("average_speed"))
            speed_max = _number_or_none(metric.get("maximum_speed"))
            stride = _number_or_none(metric.get("stride_length"))
            cadence = _number_or_none(metric.get("cadence"))
            posture = _number_or_none(metric.get("posture_score"))

            for name, value in (
                ("posture", posture),
                ("speed", speed_avg),
                ("stride", stride),
                ("cadence", cadence),
            ):
                if value is None:
                    missing[name] += 1
                elif value == 0:
                    zeros[name] += 1

            if speed_avg is not None:
                speed_values.append(speed_avg)
            if speed_max is not None:
                speed_values.append(speed_max)
            for _, value in series:
                if value > SPEED_OUTLIER_THRESHOLD:
                    speed_values.append(value)

            athlete = athletes.get(str(test.get("athlete_id")))
            if athlete is None:
                skipped.append(
                    {
                        "session_id": _session_id(analysis),
                        "reason": "referenced athlete is not in the export",
                    }
                )
                continue
            payload = {
                "session_id": _session_id(analysis),
                "athlete_id": "ATL-{0:04d}".format(_number(test.get("athlete_id"))),
                "timestamp": _iso_timestamp(
                    analysis.get("completed_at")
                    or analysis.get("started_at")
                    or analysis.get("created_at")
                ),
                "test_type": "prueba de {0} m con salida de tacos".format(
                    TEST_DISTANCE_METERS
                ),
                "metrics": {
                    "posture": (
                        {
                            "value": posture,
                            "unit": UNIT_POSTURE,
                            "parameter": "posture_score",
                        }
                        if posture is not None
                        else None
                    ),
                    "speed": (
                        {
                            "avg": speed_avg,
                            "max": speed_max,
                            "unit": UNIT_SPEED,
                            "series": [{"t": t, "v": v} for t, v in series],
                        }
                        if speed_avg is not None
                        else None
                    ),
                    "stride": (
                        {"avg": stride, "unit": UNIT_STRIDE}
                        if stride is not None
                        else None
                    ),
                    "cadence": (
                        {"avg": cadence, "unit": UNIT_CADENCE}
                        if cadence is not None
                        else None
                    ),
                },
                "metadata": {
                    "source_system": SOURCE_SYSTEM,
                    "schema_version": SCHEMA_VERSION,
                    "observation": (
                        "Exportación CSV de la Fase I; atleta seudónimo "
                        "({0}); serie de velocidad recortada al tramo de "
                        "desplazamiento ({1} cuadros excluidos); "
                        "posture_score se conserva con la unidad declarada "
                        "por la fuente ('score'), no es un ángulo en grados."
                    ).format(
                        "ATL-{0:04d}".format(_number(test.get("athlete_id"))),
                        trimmed,
                    ),
                },
            }
            payloads.append(payload)

        outliers = [value for value in speed_values if value > SPEED_OUTLIER_THRESHOLD]
        profile = {
            "source_dir": str(self.csv_dir),
            "source_system": SOURCE_SYSTEM,
            "schema_version": SCHEMA_VERSION,
            "rows_read": {
                name: len(self._load(name))
                for name in ("athletes", "tests", "videos", "analyses", "metrics", "frame_metrics")
            },
            "candidates": len(analyses),
            "payloads_built": len(payloads),
            "skipped": skipped,
            "missing_values": dict(missing),
            "zero_values_declared_by_source": dict(zeros),
            "speed_series": {
                "frames_read": frames_total,
                "frames_trimmed": frames_trimmed,
                "outlier_threshold_m_s": SPEED_OUTLIER_THRESHOLD,
                "outlier_count": len(outliers),
                "max_observed_m_s": round(max(speed_values), 3) if speed_values else None,
            },
            "notes": [
                "Los ceros declarados por el origen se renderizan tal cual; "
                "el perfil los lista para verificación con la Fase I.",
                "Los valores por encima del umbral de velocidad se marcan como "
                "atípicos en el perfil y NO se eliminan del registro.",
            ],
        }
        return Fase1Batch(payloads=payloads, profile=profile)

    # -- helpers -----------------------------------------------------------
    def _load(self, name: str) -> list:
        path = self.csv_dir / "{0}.csv".format(name)
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


def _session_id(analysis: dict) -> str:
    return "SES-F1-{0}".format(analysis.get("id"))


def _iso_timestamp(value) -> Optional[str]:
    """Normalize the export's timestamp into strict ISO 8601.

    The Fase I export writes ``2026-10-03 22:44:45.897384+00`` (space
    separator, short offset). The contract requires ISO 8601, so the
    adapter rewrites it to ``2026-10-03T22:44:45.897384+00:00`` instead of
    loosening the validator.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # Python 3.9's %z accepts ±HH:MM but not the export's short ±HH form.
    text = re.sub(r"([+-]\d{2})$", r"\1:00", text)
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return None


def _number(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _number_or_none(value) -> Optional[float]:
    """Parse a numeric cell; empty/blank means 'not captured' (→ null)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _speed_series(rows: list) -> tuple:
    """Series trimmed to the displacement span (documented transformation).

    Fase I records ``speed = 0`` for the frames before the start and after
    the finish; keeping them would render a flat, misleading curve. The
    number of excluded frames is reported in the profile and in
    ``metadata.observation``.
    """
    points = []
    for row in rows:
        speed = _number_or_none(row.get("speed"))
        # The Fase I export names the column ``timestamp`` (seconds); the
        # adapter also accepts ``timestamp_seconds`` for other exports.
        raw_time = row.get("timestamp_seconds")
        if raw_time is None or str(raw_time).strip() == "":
            raw_time = row.get("timestamp")
        timestamp = _number_or_none(raw_time)
        if speed is None or timestamp is None:
            continue
        points.append((timestamp, speed))

    nonzero = [index for index, (_, speed) in enumerate(points) if speed > 0]
    if not nonzero:
        return [], len(points)
    first, last = nonzero[0], nonzero[-1]
    trimmed = len(points) - (last - first + 1)
    return points[first : last + 1], trimmed
