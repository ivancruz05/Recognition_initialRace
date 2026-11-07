"""Pruebas del adaptador CSV con un export sintético y local."""

from __future__ import annotations

import csv

from apps.sessions.domain import AvailabilityStatus
from apps.sessions.infrastructure.file_ingest import Fase1ExportAdapter


TABLES = {
    "athletes": [
        {"id": "1", "first_name": "Ana", "last_name": "Test"},
    ],
    "tests": [
        {"id": "10", "athlete_id": "1", "distance": "10"},
        {"id": "11", "athlete_id": "1", "distance": "20"},
        {"id": "12", "athlete_id": "1", "distance": "10"},
    ],
    "videos": [
        {"id": "20", "test_id": "10"},
        {"id": "21", "test_id": "11"},
        {"id": "22", "test_id": "12"},
        {"id": "23", "test_id": "10"},
    ],
    "analyses": [
        {"id": "30", "video_id": "20", "status": "COMPLETED", "completed_at": "2026-10-03 22:44:45.897384+00"},
        {"id": "31", "video_id": "21", "status": "COMPLETED", "completed_at": "2026-10-03 22:44:45+00"},
        {"id": "32", "video_id": "22", "status": "COMPLETED", "completed_at": "2026-10-03 22:44:45+00"},
        {"id": "33", "video_id": "23", "status": "PENDING", "completed_at": ""},
    ],
    "metrics": [
        {"analysis_id": "30", "average_speed": "5.0", "maximum_speed": "13.0", "stride_length": "", "cadence": "2.5", "posture_score": "3.2"},
    ],
    "frame_metrics": [
        {"analysis_id": "30", "frame_number": "0", "timestamp": "0", "speed": "0"},
        {"analysis_id": "30", "frame_number": "1", "timestamp": "0.1", "speed": "5"},
        {"analysis_id": "30", "frame_number": "2", "timestamp": "0.2", "speed": "13"},
        {"analysis_id": "30", "frame_number": "3", "timestamp": "0.3", "speed": "0"},
    ],
}


def _write_export(path):
    for name, rows in TABLES.items():
        columns = list(rows[0]) if rows else []
        with (path / (name + ".csv")).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)


def test_adapter_filtra_distancia_estado_y_fila_de_metricas(tmp_path):
    _write_export(tmp_path)
    batch = Fase1ExportAdapter(tmp_path).load()
    assert [item["session_id"] for item in batch.payloads] == ["SES-F1-30"]
    reasons = [item["reason"] for item in batch.profile["skipped"]]
    assert any("out of scope" in reason for reason in reasons)
    assert any("not completed" in reason for reason in reasons)


def test_adapter_preserva_nulos_recorta_serie_normaliza_fecha_y_perfilar(tmp_path):
    _write_export(tmp_path)
    batch = Fase1ExportAdapter(tmp_path).load()
    payload = batch.payloads[0]
    assert payload["timestamp"] == "2026-10-03T22:44:45.897384+00:00"
    assert payload["metrics"]["stride"] is None
    assert payload["metrics"]["speed"]["series"] == [
        {"t": 0.1, "v": 5.0}, {"t": 0.2, "v": 13.0}
    ]
    assert "2 cuadros excluidos" in payload["metadata"]["observation"]
    assert batch.profile["candidates"] == 4
    assert batch.profile["payloads_built"] == 1
    assert batch.profile["missing_values"]["stride"] == 1
    assert batch.profile["speed_series"]["frames_trimmed"] == 2
    # La serie conserva el atípico; el perfil solo lo señala.
    assert batch.profile["speed_series"]["outlier_count"] >= 1
