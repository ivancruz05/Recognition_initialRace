"""Analysis pipelines for common workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from detection.metrics.biomechanics import BiomechanicsAnalyzer
from detection.metrics.measurements import BodyMeasurementAnalyzer
from detection.entities import BodyMeasurements, DepthFrame
from detection.interfaces import PoseDetectorInterface
from detection.vision.pose import PoseDetector, landmarks_to_array
from detection.vision.view_detection import ViewType
from detection.vision.pose_validation import validate_pose
from detection.vision.pose_constants import MIN_VALID_FRAMES


class MeasurementPipeline:
    """Simplified pipeline for body measurements only."""

    def __init__(
        self,
        required_view: ViewType = ViewType.PROFILE,
        pose_detector: Optional[PoseDetectorInterface] = None,
    ):
        """Build the pipeline.

        pose_detector is injectable so callers (notably the HTTP backend) can
        supply a fake and run without loading MediaPipe.
        """
        self.pose_detector = pose_detector or PoseDetector(model_complexity=2)
        self.body_measurer = BodyMeasurementAnalyzer()
        self.required_view = required_view

    def close(self) -> None:
        """Release resources held by the pipeline."""
        self.pose_detector.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def measure_video(
        self,
        video_path: str,
        known_height_cm: Optional[float] = None,
        sample_frames: int = 30,
        strict: bool = True,
    ) -> Dict:
        """
        Measure body dimensions from a standard video file.

        Returns:
            dict con 'measurements', 'validation_summary', 'rejected_frames'
        """
        return self._measure_standard(video_path, known_height_cm, sample_frames, strict)

    def _measure_standard(
        self, video_path: str, known_height_cm: Optional[float],
        sample_frames: int, strict: bool,
    ) -> Dict:
        """Measure from standard video file."""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        measurements_list = []
        rejected = 0
        frame_idx = 0
        view_counts = {"front": 0, "profile": 0, "diagonal": 0}

        while cap.isOpened() and len(measurements_list) < sample_frames:
            ret, bgr = cap.read()
            if not ret:
                break

            if sample_frames <= 0:
                sample_frames = 30
            if frame_idx % max(1, frame_count // sample_frames) == 0:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                landmarks = self.pose_detector.detect(rgb)
                if landmarks is None:
                    frame_idx += 1
                    continue

                # --- GATE: validar pose antes de medir ---
                lm_array = landmarks_to_array(landmarks)
                validation = validate_pose(lm_array, self.required_view)
                view_type = validation.view.view_type.value if validation.view else "unknown"
                view_counts[view_type] = view_counts.get(view_type, 0) + 1

                if not validation.is_valid:
                    rejected += 1
                    if strict:
                        frame_idx += 1
                        continue

                if validation.is_valid:
                    measurement = self.body_measurer.measure(
                        landmarks,
                        known_height_cm=known_height_cm,
                        image_shape=(height, width),
                    )
                    measurements_list.append(measurement)

            frame_idx += 1

        cap.release()
        return self._build_result(measurements_list, rejected, view_counts)

    def _build_result(
        self,
        measurements: List[BodyMeasurements],
        rejected: int,
        view_counts: Dict[str, int],
    ) -> Dict:
        """Construye el resultado con validación y mediciones."""
        if not measurements:
            return {
                "measurements": BodyMeasurements(
                    height_cm=0, leg_length_cm=0, arm_length_cm=0,
                    torso_length_cm=0, foot_length_cm=0, shoulder_width_cm=0,
                ),
                "validation_summary": {
                    "total_valid": 0,
                    "total_rejected": rejected,
                    "view_distribution": view_counts,
                    "status": "SIN_FRAMES_VÁLIDOS",
                },
                "rejected_frames": rejected,
            }

        n = len(measurements)
        avg = BodyMeasurements(
            height_cm=sum(m.height_cm for m in measurements) / n,
            leg_length_cm=sum(m.leg_length_cm for m in measurements) / n,
            arm_length_cm=sum(m.arm_length_cm for m in measurements) / n,
            torso_length_cm=sum(m.torso_length_cm for m in measurements) / n,
            foot_length_cm=sum(m.foot_length_cm for m in measurements) / n,
            shoulder_width_cm=sum(m.shoulder_width_cm for m in measurements) / n,
            confidence=sum(m.confidence for m in measurements) / n,
            depth_valid_ratio=sum(m.depth_valid_ratio for m in measurements) / n,
        )

        status = "OK" if n >= MIN_VALID_FRAMES else "POCOS_FRAMES"

        return {
            "measurements": avg,
            "validation_summary": {
                "total_valid": n,
                "total_rejected": rejected,
                "view_distribution": view_counts,
                "status": status,
            },
            "rejected_frames": rejected,
        }


class AnalysisPipeline:
    """Full sprint analysis pipeline."""

    def __init__(self):
        self.pose_detector = PoseDetector(model_complexity=2)
        self.biomechanics = BiomechanicsAnalyzer()
        self.body_measurer = BodyMeasurementAnalyzer()

    def close(self) -> None:
        """Release resources held by the pipeline."""
        self.pose_detector.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def analyze_frame(
        self,
        frame: DepthFrame,
        image_shape: tuple,
    ) -> Optional[Dict]:
        """Analyze a single frame."""
        import cv2

        if frame.rgb is None:
            return None

        landmarks = self.pose_detector.detect(frame.rgb)
        if landmarks is None:
            return None

        metrics = self.biomechanics.analyze(landmarks)

        return {
            "frame_index": frame.frame_index,
            "quality_score": metrics.quality_score,
            "angles": {
                "left_knee": metrics.angles.left_knee,
                "right_knee": metrics.angles.right_knee,
                "left_hip": metrics.angles.left_hip,
                "right_hip": metrics.angles.right_hip,
                "trunk": metrics.angles.trunk_angle,
            },
            "recommendations": self.biomechanics._generate_recommendations(metrics.angles),
        }
