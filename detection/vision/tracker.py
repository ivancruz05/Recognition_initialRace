"""Athlete detection and tracking using YOLOv8 + ByteTrack."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from drone_analysis.domain.models import TrackingResult


class TrackerError(Exception):
    """Raised when the tracker cannot be initialized."""


class AthleteTracker:
    """Track a single athlete across video frames with YOLOv8 and ByteTrack."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        tracker: str = "bytetrack.yaml",
        confidence_threshold: float = 0.4,
        preferred_region: Optional[Tuple[int, int, int, int]] = None,
    ):
        """
        Args:
            model_name: Ultralytics YOLO model file/path.
            tracker: Ultralytics tracker config (e.g. "bytetrack.yaml").
            confidence_threshold: minimum detection confidence.
            preferred_region: optional (x1, y1, x2, y2) ROI used to select
                the athlete when multiple people are detected.
        """
        self.model_name = model_name
        self.tracker = tracker
        self.confidence_threshold = confidence_threshold
        self.preferred_region = preferred_region
        self._model = None

    def _load_model(self):
        """Lazy-load the YOLO model (downloads weights on first call)."""
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise TrackerError("ultralytics is required for athlete tracking") from exc
            self._model = YOLO(self.model_name)
        return self._model

    def track(self, frame_bgr: np.ndarray) -> Optional[TrackingResult]:
        """Run tracking on a single BGR frame and return the athlete box."""
        model = self._load_model()
        results = model.track(
            frame_bgr,
            persist=True,
            tracker=self.tracker,
            classes=[0],  # person
            verbose=False,
            conf=self.confidence_threshold,
        )
        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            return None

        detections = self._extract_detections(results[0])
        if not detections:
            return None

        chosen = self._select_detection(detections)
        return chosen

    def reset(self) -> None:
        """Reset internal tracker state."""
        # ByteTrack state is bound to the model inference context; reloading
        # the model is the simplest way to start fresh.
        self._model = None

    def _extract_detections(self, result) -> List[TrackingResult]:
        """Convert Ultralytics result to TrackingResult objects."""
        boxes = result.boxes
        detections: List[TrackingResult] = []
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        ids = boxes.id.cpu().numpy() if boxes.id is not None else np.full(len(xyxy), -1)

        for (x1, y1, x2, y2), conf, track_id in zip(xyxy, confs, ids):
            x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
            detections.append(
                TrackingResult(
                    track_id=int(track_id),
                    bbox=(x1, y1, x2, y2),
                    confidence=float(conf),
                    center=((x1 + x2) / 2.0, (y1 + y2) / 2.0),
                )
            )
        return detections

    def _select_detection(self, detections: List[TrackingResult]) -> TrackingResult:
        """Choose the athlete among all person detections."""
        if len(detections) == 1:
            return detections[0]

        if self.preferred_region is not None:
            return max(
                detections,
                key=lambda d: self._iou(d.bbox, self.preferred_region),
            )

        # Fallback: largest detection area.
        return max(detections, key=lambda d: d.width * d.height)

    @staticmethod
    def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        """Intersection-over-union of two bounding boxes."""
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0


def crop_bbox(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    margin: float = 0.15,
    frame_shape: Optional[Tuple[int, int]] = None,
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """Crop a frame around a bounding box with an optional margin.

    Returns the cropped image and the actual crop coordinates used.
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    cw, ch = x2 - x1, y2 - y1
    dx = int(cw * margin)
    dy = int(ch * margin)

    cx1 = max(0, x1 - dx)
    cy1 = max(0, y1 - dy)
    cx2 = min(w, x2 + dx)
    cy2 = min(h, y2 + dy)

    return frame[cy1:cy2, cx1:cx2], (cx1, cy1, cx2, cy2)
