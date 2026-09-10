"""Analysis pipelines for common workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from sprint_analysis.analysis.biomechanics import BiomechanicsAnalyzer
from sprint_analysis.analysis.measurements import BodyMeasurementAnalyzer
from sprint_analysis.domain.models import BodyMeasurements, DepthFrame, PoseLandmarks
from sprint_analysis.infrastructure.lidar.r3d_parser import R3DParser
from sprint_analysis.infrastructure.pose.detector import PoseDetector


class MeasurementPipeline:
    """Simplified pipeline for body measurements only."""

    def __init__(self):
        self.pose_detector = PoseDetector(model_complexity=2)
        self.body_measurer = BodyMeasurementAnalyzer()

    def measure_video(
        self,
        video_path: str,
        known_height_cm: Optional[float] = None,
        sample_frames: int = 30,
    ) -> BodyMeasurements:
        """Measure body dimensions from a video file."""
        path = Path(video_path)

        if path.suffix.lower() == ".r3d":
            return self._measure_r3d(video_path, known_height_cm, sample_frames)
        return self._measure_standard(video_path, known_height_cm, sample_frames)

    def _measure_r3d(
        self, video_path: str, known_height_cm: Optional[float], sample_frames: int
    ) -> BodyMeasurements:
        """Measure from R3D file with LiDAR."""
        parser = R3DParser(video_path)
        info = parser.get_info()

        measurements_list = []
        for i in range(min(sample_frames, info.frame_count)):
            frame = parser.extract_frame(i)
            if frame is None or frame.rgb is None:
                continue

            import cv2
            landmarks = self.pose_detector.detect(cv2.cvtColor(frame.rgb, cv2.COLOR_BGR2RGB))
            if landmarks is None:
                continue

            measurement = self.body_measurer.measure(
                landmarks,
                frame,
                known_height_cm=known_height_cm,
                image_shape=(info.height, info.width),
            )
            measurements_list.append(measurement)

        return self._average_measurements(measurements_list)

    def _measure_standard(
        self, video_path: str, known_height_cm: Optional[float], sample_frames: int
    ) -> BodyMeasurements:
        """Measure from standard video file."""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        measurements_list = []
        frame_idx = 0

        while cap.isOpened() and len(measurements_list) < sample_frames:
            ret, bgr = cap.read()
            if not ret:
                break

            if frame_idx % max(1, frame_count // sample_frames) == 0:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                landmarks = self.pose_detector.detect(rgb)
                if landmarks:
                    measurement = self.body_measurer.measure(
                        landmarks,
                        known_height_cm=known_height_cm,
                        image_shape=(height, width),
                    )
                    measurements_list.append(measurement)

            frame_idx += 1

        cap.release()
        return self._average_measurements(measurements_list)

    def _average_measurements(self, measurements: List[BodyMeasurements]) -> BodyMeasurements:
        if not measurements:
            return BodyMeasurements(height_cm=0, leg_length_cm=0, arm_length_cm=0,
                                   torso_length_cm=0, foot_length_cm=0, shoulder_width_cm=0)

        n = len(measurements)
        return BodyMeasurements(
            height_cm=sum(m.height_cm for m in measurements) / n,
            leg_length_cm=sum(m.leg_length_cm for m in measurements) / n,
            arm_length_cm=sum(m.arm_length_cm for m in measurements) / n,
            torso_length_cm=sum(m.torso_length_cm for m in measurements) / n,
            foot_length_cm=sum(m.foot_length_cm for m in measurements) / n,
            shoulder_width_cm=sum(m.shoulder_width_cm for m in measurements) / n,
            confidence=sum(m.confidence for m in measurements) / n,
            depth_valid_ratio=sum(m.depth_valid_ratio for m in measurements) / n,
        )


class AnalysisPipeline:
    """Full sprint analysis pipeline."""

    def __init__(self):
        self.pose_detector = PoseDetector(model_complexity=2)
        self.biomechanics = BiomechanicsAnalyzer()
        self.body_measurer = BodyMeasurementAnalyzer()

    def analyze_frame(
        self,
        frame: DepthFrame,
        image_shape: tuple,
    ) -> Optional[Dict]:
        """Analyze a single frame."""
        import cv2

        if frame.rgb is None:
            return None

        landmarks = self.pose_detector.detect(cv2.cvtColor(frame.rgb, cv2.COLOR_BGR2RGB))
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
