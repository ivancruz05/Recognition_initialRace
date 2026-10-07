"""Atomic JSON manifest for the artifacts and outcome of one session."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union


PathLike = Union[str, os.PathLike]


class SessionManifestWriter:
    """Write an exclusive session manifest and atomically finalize its status.

    Create the initial ``in_progress`` record with :meth:`start`, then call
    exactly one of :meth:`complete`, :meth:`empty`, or :meth:`fail`. Final
    records are snapshots replaced atomically in the manifest's directory.
    """

    def __init__(self, path: PathLike) -> None:
        self.path = Path(path)
        self._manifest: Optional[dict[str, Any]] = None
        self._finished = False

    def start(
        self,
        *,
        session_id: str,
        athlete_id: str,
        output_csv: PathLike,
        raw_mp4: Optional[PathLike] = None,
        source_reference: Optional[str] = None,
        capture_metadata: Optional[Mapping[str, object]] = None,
    ) -> None:
        """Create an exclusive manifest with status ``in_progress``."""
        if self._manifest is not None:
            raise RuntimeError("session manifest has already been started")
        self._require_identifier(session_id, "session_id")
        self._require_identifier(athlete_id, "athlete_id")
        if source_reference is not None and not isinstance(source_reference, str):
            raise TypeError("source_reference must be a string or None")
        if capture_metadata is not None and not isinstance(capture_metadata, Mapping):
            raise TypeError("capture_metadata must be a mapping or None")

        metadata = {} if capture_metadata is None else dict(capture_metadata)
        manifest: dict[str, Any] = {
            "status": "in_progress",
            "session_id": session_id,
            "athlete_id": athlete_id,
            "output_csv": os.fspath(output_csv),
            "raw_mp4": None if raw_mp4 is None else os.fspath(raw_mp4),
            "source_reference": source_reference,
            "capture_metadata": metadata,
            "started_at_utc": self._utc_now(),
            "finished_at_utc": None,
            "frames_written": 0,
            "pose_detected": 0,
            "pose_ready": 0,
            "raw_video_frames_written": 0,
            "error_type": None,
            "error_message": None,
        }
        self._persist(manifest, exclusive=True)
        self._manifest = manifest

    def complete(
        self,
        *,
        frames_written: int,
        pose_detected: int,
        pose_ready: int,
        raw_video_frames_written: int = 0,
    ) -> None:
        """Mark the session ``complete`` after every configured output closed."""
        self._finalize(
            "complete",
            frames_written=frames_written,
            pose_detected=pose_detected,
            pose_ready=pose_ready,
            raw_video_frames_written=raw_video_frames_written,
        )

    def empty(
        self,
        *,
        frames_written: int = 0,
        pose_detected: int = 0,
        pose_ready: int = 0,
        raw_video_frames_written: int = 0,
    ) -> None:
        """Mark a successfully closed session with no CSV rows as ``empty``."""
        self._finalize(
            "empty",
            frames_written=frames_written,
            pose_detected=pose_detected,
            pose_ready=pose_ready,
            raw_video_frames_written=raw_video_frames_written,
        )

    def fail(
        self,
        error: BaseException,
        *,
        frames_written: int = 0,
        pose_detected: int = 0,
        pose_ready: int = 0,
        raw_video_frames_written: int = 0,
    ) -> None:
        """Record a failed session without deleting any partial output files."""
        if not isinstance(error, BaseException):
            raise TypeError("error must be an exception")
        self._finalize(
            "failed",
            frames_written=frames_written,
            pose_detected=pose_detected,
            pose_ready=pose_ready,
            raw_video_frames_written=raw_video_frames_written,
            error_type=type(error).__name__,
            error_message=str(error),
        )

    def _finalize(
        self,
        status: str,
        *,
        frames_written: int,
        pose_detected: int,
        pose_ready: int,
        raw_video_frames_written: int,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if self._manifest is None:
            raise RuntimeError("session manifest has not been started")
        if self._finished:
            raise RuntimeError("session manifest has already been finalized")
        self._validate_counts(
            frames_written,
            pose_detected,
            pose_ready,
            raw_video_frames_written,
        )
        if status == "complete" and frames_written == 0:
            raise ValueError("complete sessions must have at least one CSV frame")
        if status == "empty" and any(
            (frames_written, pose_detected, pose_ready, raw_video_frames_written)
        ):
            raise ValueError("empty sessions must have zero CSV, pose, and raw-video counts")

        manifest = dict(self._manifest)
        manifest.update(
            {
                "status": status,
                "finished_at_utc": self._utc_now(),
                "frames_written": frames_written,
                "pose_detected": pose_detected,
                "pose_ready": pose_ready,
                "raw_video_frames_written": raw_video_frames_written,
                "error_type": error_type,
                "error_message": error_message,
            }
        )
        self._persist(manifest, exclusive=False)
        self._manifest = manifest
        self._finished = True

    def _persist(self, manifest: dict[str, Any], *, exclusive: bool) -> None:
        parent = self.path.parent
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".{}-".format(self.path.name), suffix=".tmp", dir=os.fspath(parent)
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            if exclusive:
                # link() publishes the fully written temp file without replacing
                # an existing manifest, even if another writer races this one.
                os.link(temporary_name, os.fspath(self.path))
            else:
                os.replace(temporary_name, os.fspath(self.path))
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass

    @staticmethod
    def _validate_counts(
        frames_written: int,
        pose_detected: int,
        pose_ready: int,
        raw_video_frames_written: int,
    ) -> None:
        counts = {
            "frames_written": frames_written,
            "pose_detected": pose_detected,
            "pose_ready": pose_ready,
            "raw_video_frames_written": raw_video_frames_written,
        }
        for name, value in counts.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("{} must be a non-negative integer".format(name))
        if pose_ready > pose_detected or pose_detected > frames_written:
            raise ValueError(
                "pose counts must satisfy pose_ready <= pose_detected <= frames_written"
            )

    @staticmethod
    def _require_identifier(value: str, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("{} must be a non-empty string".format(name))

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
