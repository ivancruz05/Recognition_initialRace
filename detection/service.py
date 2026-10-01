"""Application services for orchestrating analysis workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from detection.metrics.biomechanics import BiomechanicsAnalyzer
from detection.metrics.comparison import ReferenceComparator
from detection.metrics.measurements import BodyMeasurementAnalyzer
from detection.metrics.ml_features import MLAnalyzer
from detection.entities import (
    AnalysisReport,
    BodyMeasurements,
    ComparisonResult,
    DepthFrame,
    PoseLandmarks,
    SprintMetrics,
    VideoInfo,
)
from detection.vision.pose import PoseDetector, landmarks_to_array
from detection.vision.view_detection import ViewType
from detection.vision.pose_validation import validate_pose
from detection.vision.pose_constants import MIN_VALID_FRAMES


class AnalysisService:
    """Orchestrates the complete analysis workflow."""

    def __init__(
        self,
        pose_detector: Optional[PoseDetector] = None,
        biomechanics: Optional[BiomechanicsAnalyzer] = None,
        comparator: Optional[ReferenceComparator] = None,
        body_measurer: Optional[BodyMeasurementAnalyzer] = None,
        ml_analyzer: Optional[MLAnalyzer] = None,
        required_view: ViewType = ViewType.PROFILE,
    ):
        self.pose_detector = pose_detector or PoseDetector(model_complexity=2)
        self.biomechanics = biomechanics or BiomechanicsAnalyzer()
        self.comparator = comparator or ReferenceComparator()
        self.body_measurer = body_measurer or BodyMeasurementAnalyzer()
        self.ml_analyzer = ml_analyzer or MLAnalyzer()
        self.required_view = required_view

    def close(self) -> None:
        """Release resources held by the service."""
        self.pose_detector.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def analyze_video(
        self,
        video_path: str,
        athlete_info: Optional[Dict] = None,
        sample_frames: int = 30,
        strict: bool = True,
    ) -> AnalysisReport:
        """Analyze a standard video file (mp4, mov, avi)."""
        return self._analyze_standard(video_path, athlete_info, sample_frames, strict)

    def _analyze_standard(
        self, video_path: str, athlete_info: Optional[Dict],
        sample_frames: int, strict: bool,
    ) -> AnalysisReport:
        """Analyze a standard video file (mp4, avi, etc.)."""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        try:
            info = VideoInfo(
                path=video_path,
                width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                fps=cap.get(cv2.CAP_PROP_FPS),
            )

            frames = []
            frame_idx = 0
            while cap.isOpened() and len(frames) < sample_frames:
                ret, bgr = cap.read()
                if not ret:
                    break
                if frame_idx % max(1, info.frame_count // sample_frames) == 0:
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    frames.append(DepthFrame(rgb=rgb, frame_index=frame_idx))
                frame_idx += 1
        finally:
            cap.release()

        return self._process_frames(frames, video_path, athlete_info, info, strict)

    def _process_frames(
        self,
        frames: List[DepthFrame],
        video_path: str,
        athlete_info: Optional[Dict],
        info: VideoInfo,
        strict: bool = True,
    ) -> AnalysisReport:
        """Process a list of frames through the analysis pipeline with validation."""
        athlete_info = athlete_info or {}
        measurements_list = []
        metrics_list = []
        landmarks_list = []
        rejected = 0
        view_counts = {"front": 0, "profile": 0, "diagonal": 0}

        for frame in frames:
            if frame.rgb is None:
                continue

            import cv2
            # BUG FIX 1: DepthFrame.rgb always contains RGB data now.
            # No conversion needed - detect() expects RGB.
            landmarks = self.pose_detector.detect(frame.rgb)
            if landmarks is None:
                continue

            # BUG FIX 2: In non-strict mode, process invalid frames too.
            # Only skip if strict mode is enabled AND validation failed.
            lm_array = landmarks_to_array(landmarks)
            validation = validate_pose(lm_array, self.required_view)
            view_type = validation.view.view_type.value if validation.view else "unknown"
            view_counts[view_type] = view_counts.get(view_type, 0) + 1

            if not validation.is_valid:
                rejected += 1
                if strict:
                    continue

            measurement = self.body_measurer.measure(
                landmarks,
                frame,
                known_height_cm=athlete_info.get("height_cm"),
                image_shape=(info.height, info.width),
            )
            measurements_list.append(measurement)

            metrics = self.biomechanics.analyze(landmarks)
            metrics_list.append(metrics)
            landmarks_list.append(landmarks)

        # --- Verificar mínimo de frames válidos ---
        if len(measurements_list) < MIN_VALID_FRAMES:
            return AnalysisReport(
                athlete_name=athlete_info.get("name", "Unknown"),
                video_path=video_path,
                measurements=BodyMeasurements(
                    height_cm=0, leg_length_cm=0, arm_length_cm=0,
                    torso_length_cm=0, foot_length_cm=0, shoulder_width_cm=0,
                ),
                metrics=SprintMetrics(),
                comparison=ComparisonResult(
                    recommendations=[
                        f"Video rechazado: solo {len(measurements_list)} frames válidos "
                        f"(mínimo {MIN_VALID_FRAMES}). "
                        f"Vistas detectadas: {view_counts}. "
                        f"Regrabar de perfil con la persona estática."
                    ]
                ),
            )

        avg_measurements = self._average_measurements(measurements_list)
        avg_metrics = self._average_metrics(metrics_list)
        
        # Use first valid landmarks for front/rear leg detection in comparison
        comparison_landmarks = landmarks_list[0] if landmarks_list else None
        comparison = self.comparator.compare(avg_metrics, comparison_landmarks)

        return AnalysisReport(
            athlete_name=athlete_info.get("name", "Unknown"),
            video_path=video_path,
            measurements=avg_measurements,
            metrics=avg_metrics,
            comparison=comparison,
            frames_analyzed=len(measurements_list),
        )

    def _average_measurements(self, measurements: List[BodyMeasurements]) -> BodyMeasurements:
        """Average multiple body measurements."""
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

    def _average_metrics(self, metrics: List[SprintMetrics]) -> SprintMetrics:
        """Average multiple sprint metrics."""
        n = len(metrics)
        avg_angles = type(metrics[0].angles)(
            left_knee=sum(m.angles.left_knee for m in metrics) / n,
            right_knee=sum(m.angles.right_knee for m in metrics) / n,
            left_hip=sum(m.angles.left_hip for m in metrics) / n,
            right_hip=sum(m.angles.right_hip for m in metrics) / n,
            left_ankle=sum(m.angles.left_ankle for m in metrics) / n,
            right_ankle=sum(m.angles.right_ankle for m in metrics) / n,
            trunk_angle=sum(m.angles.trunk_angle for m in metrics) / n,
        )
        return SprintMetrics(
            quality_score=sum(m.quality_score for m in metrics) / n,
            angles=avg_angles,
        )
