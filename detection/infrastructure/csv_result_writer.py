"""Incremental standard-library CSV writer for per-frame angle results."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Optional, TextIO, Union

from detection.domain.entities import BiomechanicalFrameResult, RecognitionSession
from detection.domain.landmarks import PoseLandmarkName


PathLike = Union[str, Path]


class CSVFrameResultWriter:
    """Write one flushed CSV row per analyzed frame, without buffering rows."""

    CAPTURE_METADATA_FIELDNAMES = (
        "capture_source",
        "source_reference",
        "camera_index",
        "expected_view",
        "camera_height_cm",
    )
    BASE_FIELDNAMES = (
        "session_id",
        "athlete_id",
        "frame_index",
        "timestamp_seconds",
        "pose_detected",
        "pose_ready",
        "any_angle_valid",
        "left_knee_deg",
        "right_knee_deg",
        "left_hip_deg",
        "right_hip_deg",
        "left_ankle_deg",
        "right_ankle_deg",
        "trunk_angle_deg",
    )
    LANDMARK_FIELDNAMES = tuple(
        "{}_{}".format(landmark.value, coordinate)
        for landmark in PoseLandmarkName
        for coordinate in ("x", "y", "visibility")
    )
    FIELDNAMES = CAPTURE_METADATA_FIELDNAMES + BASE_FIELDNAMES + LANDMARK_FIELDNAMES

    def __init__(
        self,
        path: PathLike,
        *,
        capture_metadata: Optional[Mapping[str, object]] = None,
    ) -> None:
        if capture_metadata is not None and not isinstance(capture_metadata, Mapping):
            raise TypeError("capture_metadata must be a mapping or None")
        self.path = Path(path)
        metadata = {} if capture_metadata is None else capture_metadata
        self._capture_metadata = {}
        for field in self.CAPTURE_METADATA_FIELDNAMES:
            value = metadata.get(field)
            self._capture_metadata[field] = "" if value is None else value
        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.DictWriter] = None
        self._session: Optional[RecognitionSession] = None
        self._rows_written = 0

    @property
    def rows_written(self) -> int:
        """Number of frame rows successfully written and flushed."""
        return self._rows_written

    def start(self, session: RecognitionSession) -> None:
        """Open the destination and write its header (no frame rows yet)."""
        if self._file is not None:
            raise RuntimeError("CSV writer is already started")
        output = self.path.open("x", newline="", encoding="utf-8")
        self._file = output
        self._writer = csv.DictWriter(output, fieldnames=self.FIELDNAMES)
        self._session = session
        self._rows_written = 0
        try:
            self._writer.writeheader()
            output.flush()
        except Exception:
            self.stop()
            raise

    def write(self, result: BiomechanicalFrameResult) -> None:
        """Append one row and flush it so completed frames are persisted."""
        if self._file is None or self._writer is None or self._session is None:
            raise RuntimeError("CSV writer has not been started")
        if result.session != self._session:
            raise ValueError("result belongs to a different recognition session")

        angles = result.angles.as_dict()
        row = {
            **self._capture_metadata,
            "session_id": result.session.session_id,
            "athlete_id": result.session.athlete_id,
            "frame_index": result.frame_index,
            "timestamp_seconds": result.timestamp_seconds,
            "pose_detected": str(result.pose_detected).lower(),
            "pose_ready": str(result.pose_ready).lower(),
            "any_angle_valid": str(
                any(result.angles.validity.values())
            ).lower(),
        }
        row.update(angles)
        for landmark_name in PoseLandmarkName:
            landmark = result.landmarks.get(landmark_name)
            row["{}_x".format(landmark_name.value)] = (
                landmark.x if landmark is not None else ""
            )
            row["{}_y".format(landmark_name.value)] = (
                landmark.y if landmark is not None else ""
            )
            row["{}_visibility".format(landmark_name.value)] = (
                landmark.visibility if landmark is not None else ""
            )
        self._writer.writerow(row)
        self._file.flush()
        self._rows_written += 1

    def stop(self) -> None:
        """Flush and close the output file; safe to call more than once."""
        output, self._file = self._file, None
        self._writer = None
        self._session = None
        if output is not None:
            try:
                output.flush()
            finally:
                output.close()
