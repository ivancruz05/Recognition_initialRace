"""Camera-to-track calibration using ArUco markers.

The module maps pixel coordinates in the drone video to real-world meters
on the athletics track. It expects at least four ArUco markers placed at
known (x, y) positions on the ground plane.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


class CalibrationError(Exception):
    """Raised when calibration cannot be performed."""


class ArUcoCalibration:
    """Calibrate a video source using ArUco markers on the track."""

    DEFAULT_MARKER_SIZE_M = 0.165  # 16.5 cm square marker
    DEFAULT_DICTIONARY = cv2.aruco.DICT_4X4_50

    def __init__(
        self,
        marker_config: Optional[Dict[int, Tuple[float, float]]] = None,
        marker_size_m: float = DEFAULT_MARKER_SIZE_M,
        dictionary: int = DEFAULT_DICTIONARY,
    ):
        """
        Args:
            marker_config: mapping marker_id -> (x_m, y_m) in world coordinates.
            marker_size_m: physical side length of a marker in meters.
            dictionary: OpenCV ArUco dictionary constant.
        """
        self.marker_config = marker_config or {}
        self.marker_size_m = marker_size_m
        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary)
        self.detector = cv2.aruco.ArucoDetector(
            self.dictionary, cv2.aruco.DetectorParameters()
        )
        self.homography: Optional[np.ndarray] = None
        self.homography_inv: Optional[np.ndarray] = None

    def set_marker_config(self, marker_config: Dict[int, Tuple[float, float]]) -> None:
        """Update the world-coordinate mapping for each marker ID."""
        self.marker_config = marker_config

    def calibrate_from_image(self, image: np.ndarray) -> bool:
        """Detect markers in *image* and compute the px->world homography.

        Returns True if a valid homography was estimated.
        """
        corners, ids, _ = self.detector.detectMarkers(image)
        if ids is None or len(ids) < 4:
            return False

        image_points: List[Tuple[float, float]] = []
        world_points: List[Tuple[float, float]] = []

        for marker_corners, marker_id in zip(corners, ids.flatten()):
            if marker_id not in self.marker_config:
                continue
            # Use the centre of the marker for matching.
            centre = marker_corners[0].mean(axis=0)
            image_points.append(tuple(centre.tolist()))
            world_points.append(self.marker_config[marker_id])

        if len(image_points) < 4:
            return False

        H, mask = cv2.findHomography(
            np.array(image_points, dtype=np.float32),
            np.array(world_points, dtype=np.float32),
            method=cv2.RANSAC,
            ransacReprojThreshold=3.0,
        )
        if H is None or mask is None or mask.sum() < 4:
            return False

        self.homography = H
        self.homography_inv = np.linalg.inv(H)
        return True

    def is_calibrated(self) -> bool:
        return self.homography is not None and self.homography_inv is not None

    def image_to_world(self, points_px: np.ndarray) -> np.ndarray:
        """Convert pixel coordinates (N, 2) to world meters (N, 2)."""
        if not self.is_calibrated():
            raise CalibrationError("Calibration has not been computed yet")
        pts = np.asarray(points_px, dtype=np.float32).reshape(-1, 1, 2)
        world = cv2.perspectiveTransform(pts, self.homography)  # type: ignore[arg-type]
        return world.reshape(-1, 2)

    def world_to_image(self, points_m: np.ndarray) -> np.ndarray:
        """Convert world coordinates (N, 2) to pixel coordinates (N, 2)."""
        if not self.is_calibrated():
            raise CalibrationError("Calibration has not been computed yet")
        pts = np.asarray(points_m, dtype=np.float32).reshape(-1, 1, 2)
        px = cv2.perspectiveTransform(pts, self.homography_inv)  # type: ignore[arg-type]
        return px.reshape(-1, 2)

    def save(self, path: str | Path) -> None:
        """Persist the homography and marker config to a JSON file."""
        if not self.is_calibrated():
            raise CalibrationError("Nothing to save; calibrate first")
        payload = {
            "homography": self.homography.tolist(),
            "marker_config": {str(k): list(v) for k, v in self.marker_config.items()},
            "marker_size_m": self.marker_size_m,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ArUcoCalibration":
        """Load a previously saved calibration."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        instance = cls(
            marker_config={int(k): tuple(v) for k, v in payload["marker_config"].items()},
            marker_size_m=payload.get("marker_size_m", cls.DEFAULT_MARKER_SIZE_M),
        )
        instance.homography = np.array(payload["homography"], dtype=np.float64)
        instance.homography_inv = np.linalg.inv(instance.homography)
        return instance

    @classmethod
    def from_scale(
        cls,
        pixels_per_meter: float,
        frame_shape: Tuple[int, int],
    ) -> "ArUcoCalibration":
        """Create an approximate calibration from a known pixels-per-meter scale.

        Useful as a fallback when ArUco markers are not available in the video.
        The y axis is also scaled by pixels_per_meter so that distances computed
        on the ground plane are approximately correct near the calibration plane.
        """
        if pixels_per_meter <= 0:
            raise ValueError("pixels_per_meter must be positive")
        scale = 1.0 / pixels_per_meter
        H = np.array([
            [scale, 0.0, 0.0],
            [0.0, scale, 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)
        instance = cls(marker_config={})
        instance.homography = H
        instance.homography_inv = np.linalg.inv(H)
        return instance


def default_track_marker_config(
    lane_width_m: float = 1.22,
    sprint_distance_m: float = 10.0,
) -> Dict[int, Tuple[float, float]]:
    """Default marker layout for a 10 m sprint lane.

    Markers 0-1 are at the start line, 2-3 at the finish line:
        0: left start  (0, 0)
        1: right start (lane_width, 0)
        2: left finish (0, sprint_distance)
        3: right finish (lane_width, sprint_distance)
    """
    return {
        0: (0.0, 0.0),
        1: (lane_width_m, 0.0),
        2: (0.0, sprint_distance_m),
        3: (lane_width_m, sprint_distance_m),
    }
