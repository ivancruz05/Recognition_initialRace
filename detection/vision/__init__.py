"""Vision adapters - the only place that touches cv2, mediapipe or ultralytics."""

from detection.vision.calibration import (
    ArUcoCalibration,
    CalibrationError,
    default_track_marker_config,
)
from detection.vision.annotate import FrameAnnotator
from detection.vision.camera import CameraManager
from detection.vision.config import Settings
from detection.vision.pose import PoseDetector
from detection.vision.stabilizer import VideoStabilizer
from detection.vision.tracker import AthleteTracker, TrackerError, crop_bbox

__all__ = [
    "ArUcoCalibration",
    "AthleteTracker",
    "CalibrationError",
    "CameraManager",
    "FrameAnnotator",
    "PoseDetector",
    "Settings",
    "TrackerError",
    "VideoStabilizer",
    "crop_bbox",
    "default_track_marker_config",
]
