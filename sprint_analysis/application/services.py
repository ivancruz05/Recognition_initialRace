"""Application services for orchestrating analysis workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from sprint_analysis.analysis.biomechanics import BiomechanicsAnalyzer
from sprint_analysis.analysis.comparison import ReferenceComparator
from sprint_analysis.analysis.measurements import BodyMeasurementAnalyzer
from sprint_analysis.analysis.ml import MLAnalyzer
from sprint_analysis.domain.models import (
    AnalysisReport,
    BodyMeasurements,
    ComparisonResult,
    DepthFrame,
    PoseLandmarks,
    SprintMetrics,
    VideoInfo,
)
from sprint_analysis.infrastructure.lidar.r3d_parser import R3DParser
from sprint_analysis.infrastructure.pose.detector import PoseDetector


class AnalysisService:
    """Orchestrates the complete analysis workflow."""

    def __init__(
        self,
        pose_detector: Optional[PoseDetector] = None,
        biomechanics: Optional[BiomechanicsAnalyzer] = None,
        comparator: Optional[ReferenceComparator] = None,
        body_measurer: Optional[BodyMeasurementAnalyzer] = None,
        ml_analyzer: Optional[MLAnalyzer] = None,
    ):
        self.pose_detector = pose_detector or PoseDetector(model_complexity=2)
        self.biomechanics = biomechanics or BiomechanicsAnalyzer()
        self.comparator = comparator or ReferenceComparator()
        self.body_measurer = body_measurer or BodyMeasurementAnalyzer()
        self.ml_analyzer = ml_analyzer or MLAnalyzer()

    def analyze_video(
        self,
        video_path: str,
        athlete_info: Optional[Dict] = None,
        sample_frames: int = 30,
    ) -> AnalysisReport:
        """Analyze a video file (r3d or mp4)."""
        path = Path(video_path)

        if path.suffix.lower() == ".r3d":
            return self._analyze_r3d(video_path, athlete_info, sample_frames)
        return self._analyze_standard(video_path, athlete_info, sample_frames)

    def _analyze_r3d(
        self, video_path: str, athlete_info: Optional[Dict], sample_frames: int
    ) -> AnalysisReport:
        """Analyze an R3D file with LiDAR depth."""
        parser = R3DParser(video_path)
        info = parser.get_info()

        frames = []
        for i in range(min(sample_frames, info.frame_count)):
            frame = parser.extract_frame(i)
            if frame is not None:
                frames.append(frame)

        return self._process_frames(
            frames, video_path, athlete_info, info
        )

    def _analyze_standard(
        self, video_path: str, athlete_info: Optional[Dict], sample_frames: int
    ) -> AnalysisReport:
        """Analyze a standard video file (mp4, avi, etc.)."""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

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
        cap.release()

        return self._process_frames(frames, video_path, athlete_info, info)

    def _process_frames(
        self,
        frames: List[DepthFrame],
        video_path: str,
        athlete_info: Optional[Dict],
        info: VideoInfo,
    ) -> AnalysisReport:
        """Process a list of frames through the analysis pipeline."""
        athlete_info = athlete_info or {}
        measurements_list = []
        metrics_list = []

        for frame in frames:
            if frame.rgb is None:
                continue

            import cv2
            landmarks = self.pose_detector.detect(cv2.cvtColor(frame.rgb, cv2.COLOR_BGR2RGB))
            if landmarks is None:
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

        if not measurements_list:
            return AnalysisReport(
                athlete_name=athlete_info.get("name", "Unknown"),
                video_path=video_path,
                measurements=BodyMeasurements(height_cm=0, leg_length_cm=0, arm_length_cm=0,
                                             torso_length_cm=0, foot_length_cm=0, shoulder_width_cm=0),
                metrics=SprintMetrics(),
                comparison=ComparisonResult(),
            )

        avg_measurements = self._average_measurements(measurements_list)
        avg_metrics = self._average_metrics(metrics_list)
        comparison = self.comparator.compare(avg_metrics)

        return AnalysisReport(
            athlete_name=athlete_info.get("name", "Unknown"),
            video_path=video_path,
            measurements=avg_measurements,
            metrics=avg_metrics,
            comparison=comparison,
            frames_analyzed=len(frames),
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
