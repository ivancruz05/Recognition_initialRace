"""End-to-end drone video analysis pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from drone_analysis.analysis.biomechanics import BiomechanicsAnalyzer
from drone_analysis.analysis.kinematics import KinematicsAnalyzer
from drone_analysis.domain.models import KinematicsResult, PoseLandmarks, TrackingResult
from drone_analysis.infrastructure.calibration.aruco import ArUcoCalibration
from drone_analysis.infrastructure.pose.detector import PoseDetector
from drone_analysis.infrastructure.tracking.athlete_tracker import AthleteTracker, crop_bbox
from drone_analysis.infrastructure.video.stabilizer import VideoStabilizer


@dataclass
class DroneAnalysisConfig:
    """Configuration for the drone analysis pipeline."""
    use_stabilization: bool = False
    yolo_model: str = "yolov8n.pt"
    tracker: str = "bytetrack.yaml"
    detection_confidence: float = 0.4
    start_region: Optional[Tuple[int, int, int, int]] = None
    sample_interval: int = 1
    max_frames: Optional[int] = None
    pose_margin: float = 0.15


@dataclass
class DroneAnalysisReport:
    """Report produced by the drone analysis pipeline."""
    video_path: str
    fps: float
    frames_processed: int
    calibration_valid: bool
    tracking: List[TrackingResult] = field(default_factory=list)
    landmarks_sequence: List[PoseLandmarks] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    kinematics: Optional[KinematicsResult] = None
    posture_score: float = 0.0
    trunk_angle_deg: float = 0.0
    variables: Dict[str, float] = field(default_factory=dict)


class DroneAnalyzer:
    """Run the complete drone video analysis pipeline."""

    def __init__(
        self,
        calibration: ArUcoCalibration,
        config: Optional[DroneAnalysisConfig] = None,
    ):
        self.calibration = calibration
        self.config = config or DroneAnalysisConfig()
        self.pose_detector = PoseDetector(model_complexity=2)
        self.biomechanics = BiomechanicsAnalyzer()
        self.tracker = AthleteTracker(
            model_name=self.config.yolo_model,
            tracker=self.config.tracker,
            confidence_threshold=self.config.detection_confidence,
            preferred_region=self.config.start_region,
        )
        self.stabilizer: Optional[VideoStabilizer] = None
        if self.config.use_stabilization:
            self.stabilizer = VideoStabilizer(transform_type="similarity")

    def close(self) -> None:
        self.pose_detector.close()

    def analyze_video(
        self,
        video_path: str,
        output_video_path: Optional[str] = None,
    ) -> DroneAnalysisReport:
        """Process a drone video and return a report."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_shape = (height, width)

        writer: Optional[cv2.VideoWriter] = None
        if output_video_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

        report = DroneAnalysisReport(
            video_path=video_path,
            fps=fps,
            frames_processed=0,
            calibration_valid=self.calibration.is_calibrated(),
        )

        frame_idx = 0
        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break

            if self.config.max_frames is not None and frame_idx >= self.config.max_frames:
                break

            if frame_idx % self.config.sample_interval != 0:
                frame_idx += 1
                continue

            timestamp = frame_idx / fps
            processed = self._process_frame(frame_bgr, frame_shape, frame_idx, timestamp)

            report.tracking.append(processed["tracking"])
            report.landmarks_sequence.append(processed["landmarks"])
            report.timestamps.append(timestamp)
            report.frames_processed += 1

            if writer is not None:
                annotated = self._annotate_frame(
                    frame_bgr,
                    processed["tracking"],
                    processed["landmarks"],
                    frame_shape,
                )
                writer.write(annotated)

            frame_idx += 1

        cap.release()
        if writer is not None:
            writer.release()

        self._compute_kinematics(report, frame_shape)
        self._compute_posture(report)
        self._build_variables(report)
        return report

    def _process_frame(
        self,
        frame_bgr: np.ndarray,
        frame_shape: Tuple[int, int],
        frame_idx: int,
        timestamp: float,
    ) -> Dict:
        """Track and estimate pose for a single frame."""
        working_frame = frame_bgr
        if self.stabilizer is not None:
            if frame_idx == 0:
                self.stabilizer.set_reference(frame_bgr)
            else:
                working_frame = self.stabilizer.stabilize(frame_bgr)

        tracking_result = self.tracker.track(working_frame)
        landmarks: Optional[PoseLandmarks] = None
        if tracking_result is not None:
            landmarks = self.pose_detector.detect_in_roi(
                working_frame,
                tracking_result.bbox,
            )

        return {
            "tracking": tracking_result,
            "landmarks": landmarks,
            "timestamp": timestamp,
        }

    @staticmethod
    def _annotate_frame(
        frame_bgr: np.ndarray,
        tracking: Optional[TrackingResult],
        landmarks: Optional[PoseLandmarks],
        frame_shape: Tuple[int, int],
    ) -> np.ndarray:
        """Draw tracking box and pose on the frame."""
        annotated = frame_bgr.copy()
        h, w = frame_shape[:2]

        if tracking is not None:
            x1, y1, x2, y2 = tracking.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"ID:{tracking.track_id} {tracking.confidence:.2f}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        if landmarks is not None:
            for lm in landmarks.landmarks.values():
                if lm.visibility < 0.5:
                    continue
                px = int(lm.x * w)
                py = int(lm.y * h)
                cv2.circle(annotated, (px, py), 2, (0, 0, 255), -1)

        return annotated

    def _compute_kinematics(
        self,
        report: DroneAnalysisReport,
        frame_shape: Tuple[int, int],
    ) -> None:
        """Compute velocity, stride length and cadence."""
        valid_landmarks = [
            lm for lm in report.landmarks_sequence if lm is not None and lm.is_valid
        ]
        if len(valid_landmarks) < 3 or not self.calibration.is_calibrated():
            return

        analyzer = KinematicsAnalyzer(self.calibration)
        report.kinematics = analyzer.analyze(
            report.landmarks_sequence,
            report.timestamps,
            frame_shape,
        )

    def _compute_posture(self, report: DroneAnalysisReport) -> None:
        """Compute average posture score and trunk angle."""
        scores = []
        trunk_angles = []
        for lm in report.landmarks_sequence:
            if lm is None or not lm.is_valid:
                continue
            metrics = self.biomechanics.analyze(lm)
            scores.append(metrics.quality_score)
            trunk_angles.append(metrics.angles.trunk_angle)

        if scores:
            report.posture_score = float(np.mean(scores))
        if trunk_angles:
            report.trunk_angle_deg = float(np.mean(trunk_angles))

    @staticmethod
    def _build_variables(report: DroneAnalysisReport) -> None:
        """Populate the four project variables for validation/export."""
        variables: Dict[str, float] = {
            "postura": report.posture_score,
            "tronco_deg": report.trunk_angle_deg,
        }

        if report.kinematics is not None:
            variables["velocidad"] = report.kinematics.max_velocity_ms
            variables["velocidad_media"] = report.kinematics.average_velocity_ms
            variables["longitud_zancada"] = (
                float(np.mean(report.kinematics.stride_length_m))
                if report.kinematics.stride_length_m else 0.0
            )
            variables["cadencia"] = (
                report.kinematics.cadence_steps_per_s[0]
                if report.kinematics.cadence_steps_per_s else 0.0
            )
            variables["distancia_total_m"] = report.kinematics.total_distance_m

        report.variables = variables

    @staticmethod
    def report_to_dict(report: DroneAnalysisReport) -> Dict:
        """Serialize the report to a plain dict."""
        return {
            "video_path": report.video_path,
            "fps": report.fps,
            "frames_processed": report.frames_processed,
            "calibration_valid": report.calibration_valid,
            "posture_score": report.posture_score,
            "trunk_angle_deg": report.trunk_angle_deg,
            "variables": report.variables,
            "kinematics": {
                "max_velocity_ms": report.kinematics.max_velocity_ms if report.kinematics else None,
                "average_velocity_ms": report.kinematics.average_velocity_ms if report.kinematics else None,
                "total_distance_m": report.kinematics.total_distance_m if report.kinematics else None,
                "cadence_steps_per_s": report.kinematics.cadence_steps_per_s[0] if report.kinematics else None,
                "stride_lengths_m": report.kinematics.stride_length_m if report.kinematics else [],
            },
        }

    @staticmethod
    def save_report(report: DroneAnalysisReport, path: str | Path) -> None:
        """Save a JSON report."""
        Path(path).write_text(
            json.dumps(DroneAnalyzer.report_to_dict(report), indent=2),
            encoding="utf-8",
        )
