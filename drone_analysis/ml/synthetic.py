"""Synthetic dataset generation for sprint biomechanics and machine learning."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


@dataclass
class SyntheticDatasetConfig:
    """Parameters controlling the synthetic dataset."""

    n_athletes: int = 200
    min_trials: int = 3
    max_trials: int = 5
    fps: int = 30
    seed: int = 2026
    noise_level: float = 0.15
    outlier_rate: float = 0.05
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    sprint_distance_m: float = 10.0
    max_frames_per_trial: Optional[int] = None

    def __post_init__(self) -> None:
        if self.n_athletes < 3:
            raise ValueError("n_athletes must be at least 3")
        if self.min_trials < 1 or self.max_trials < self.min_trials:
            raise ValueError("trials must satisfy min_trials >= 1 and max_trials >= min_trials")
        if self.fps < 1:
            raise ValueError("fps must be positive")
        if not 0 <= self.noise_level <= 1:
            raise ValueError("noise_level must be between 0 and 1")
        if not 0 <= self.outlier_rate <= 1:
            raise ValueError("outlier_rate must be between 0 and 1")
        if not 0 < self.train_ratio < 1:
            raise ValueError("train_ratio must be between 0 and 1")
        if not 0 < self.val_ratio < 1:
            raise ValueError("val_ratio must be between 0 and 1")
        if self.train_ratio + self.val_ratio >= 1:
            raise ValueError("train_ratio + val_ratio must be less than 1")
        if self.sprint_distance_m <= 0:
            raise ValueError("sprint_distance_m must be positive")
        if self.max_frames_per_trial is not None and self.max_frames_per_trial < 6:
            raise ValueError("max_frames_per_trial must be at least 6")


@dataclass
class SyntheticDatasetSummary:
    """Summary of generated dataset files and row counts."""

    output_dir: str
    athletes: int
    trials: int
    frames: int
    split_counts: Dict[str, int]
    files: Dict[str, str]


class SyntheticDatasetGenerator:
    """Generate reproducible synthetic sprint trials and frame-level features."""

    TRIAL_COLUMNS = [
        "trial_id",
        "athlete_id",
        "session_id",
        "split",
        "trial_index",
        "sex",
        "sex_encoded",
        "age",
        "height_cm",
        "weight_kg",
        "experience_years",
        "training_level",
        "camera_height_m",
        "camera_distance_m",
        "camera_angle_deg",
        "fps",
        "lighting_lux",
        "signal_quality",
        "visibility_ratio",
        "tracking_confidence",
        "pose_confidence",
        "avg_knee_angle",
        "avg_hip_angle",
        "trunk_angle",
        "knee_symmetry",
        "hip_symmetry",
        "posture_score",
        "reaction_time_s",
        "time_10m_s",
        "average_speed_ms",
        "max_speed_ms",
        "stride_length_m",
        "cadence_steps_s",
        "quality_class",
        "quality_flag",
        "is_outlier",
    ]

    FRAME_COLUMNS = [
        "trial_id",
        "athlete_id",
        "split",
        "frame_index",
        "time_s",
        "progress_m",
        "speed_ms",
        "stride_length_m",
        "cadence_steps_s",
        "hip_x_m",
        "hip_y_m",
        "knee_angle_deg",
        "hip_angle_deg",
        "trunk_angle_deg",
        "knee_symmetry_deg",
        "hip_symmetry_deg",
        "posture_score",
        "pose_confidence",
        "tracking_confidence",
        "phase",
    ]

    def __init__(self, config: Optional[SyntheticDatasetConfig] = None):
        self.config = config or SyntheticDatasetConfig()
        self.rng = np.random.default_rng(self.config.seed)

    def generate(self, output_dir: str | Path) -> SyntheticDatasetSummary:
        """Generate all dataset files and return a summary."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        athletes = self._generate_athletes()
        split_map = self._assign_splits([athlete["athlete_id"] for athlete in athletes])
        trials: List[Dict] = []
        frames: List[Dict] = []

        for athlete in athletes:
            n_trials = int(self.rng.integers(self.config.min_trials, self.config.max_trials + 1))
            for trial_index in range(n_trials):
                trial, trial_frames = self._generate_trial(
                    athlete=athlete,
                    trial_index=trial_index,
                    split=split_map[athlete["athlete_id"]],
                )
                trials.append(trial)
                frames.extend(trial_frames)

        athletes_path = output_path / "athletes.csv"
        trials_path = output_path / "trials.csv"
        frames_path = output_path / "frame_features.csv"
        split_path = output_path / "splits.csv"
        metadata_path = output_path / "dataset_metadata.json"

        self._write_csv(athletes_path, athletes)
        self._write_csv(trials_path, trials)
        self._write_csv(frames_path, frames)
        self._write_csv(split_path, [
            {"athlete_id": athlete_id, "split": split}
            for athlete_id, split in split_map.items()
        ])

        split_counts = {
            split: sum(1 for trial in trials if trial["split"] == split)
            for split in ("train", "val", "test")
        }
        metadata = {
            "dataset_name": "synthetic_sprint_biomechanics",
            "version": "1.0.0",
            "seed": self.config.seed,
            "synthetic": True,
            "contains_personal_data": False,
            "description": "Synthetic 10 m sprint trials for posture, velocity, stride length and cadence modeling.",
            "tables": {
                "athletes.csv": "One row per synthetic athlete.",
                "trials.csv": "One row per trial; target for time_10m_s and quality_class.",
                "frame_features.csv": "Time-series features extracted at the configured frame rate.",
                "splits.csv": "Athlete-level train/validation/test split.",
            },
            "feature_columns": [
                "age", "height_cm", "weight_kg", "experience_years", "training_level", "sex_encoded",
                "avg_knee_angle", "avg_hip_angle", "trunk_angle", "knee_symmetry",
                "hip_symmetry", "posture_score", "camera_height_m", "camera_distance_m",
                "camera_angle_deg", "lighting_lux", "signal_quality", "visibility_ratio",
                "tracking_confidence", "pose_confidence",
            ],
            "targets": {
                "time_10m_s": "10 m sprint time in seconds; regression target.",
                "quality_class": "buena, regular or mala; classification target.",
                "average_speed_ms": "Average speed in m/s.",
                "max_speed_ms": "Maximum speed in m/s.",
                "stride_length_m": "Distance per step in meters.",
                "cadence_steps_s": "Steps per second.",
            },
            "units": {
                "angles": "degrees",
                "distances": "meters",
                "speed": "m/s",
                "cadence": "steps/s",
                "time": "seconds",
            },
            "generation": {
                "n_athletes": self.config.n_athletes,
                "min_trials": self.config.min_trials,
                "max_trials": self.config.max_trials,
                "fps": self.config.fps,
                "noise_level": self.config.noise_level,
                "outlier_rate": self.config.outlier_rate,
                "train_ratio": self.config.train_ratio,
                "val_ratio": self.config.val_ratio,
                "sprint_distance_m": self.config.sprint_distance_m,
                "max_frames_per_trial": self.config.max_frames_per_trial,
            },
            "rows": {
                "athletes": len(athletes),
                "trials": len(trials),
                "frames": len(frames),
                "trials_by_split": split_counts,
            },
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return SyntheticDatasetSummary(
            output_dir=str(output_path),
            athletes=len(athletes),
            trials=len(trials),
            frames=len(frames),
            split_counts=split_counts,
            files={
                "athletes": str(athletes_path),
                "trials": str(trials_path),
                "frames": str(frames_path),
                "splits": str(split_path),
                "metadata": str(metadata_path),
            },
        )

    def _generate_athletes(self) -> List[Dict]:
        athletes = []
        for index in range(self.config.n_athletes):
            sex = str(self.rng.choice(["F", "M"], p=[0.45, 0.55]))
            height_mean = 164.0 if sex == "F" else 176.0
            height = float(np.clip(self.rng.normal(height_mean, 6.0), 150.0, 200.0))
            bmi = float(np.clip(self.rng.normal(23.5, 2.5), 18.0, 32.0))
            weight = float(np.clip(bmi * (height / 100.0) ** 2, 45.0, 110.0))
            age = int(np.clip(round(self.rng.normal(21.0, 3.0)), 17, 32))
            experience = int(np.clip(round(self.rng.gamma(1.6, 2.2)), 0, 15))
            training_level = int(np.clip(round(1.0 + experience / 3.0 + self.rng.normal(0, 0.7)), 1, 5))
            ability = float(self.rng.normal(0.0, 0.8) + (experience - 4) * 0.035 + (training_level - 3) * 0.10)
            athletes.append({
                "athlete_id": f"SYN_A{index + 1:04d}",
                "sex": sex,
                "sex_encoded": 1 if sex == "M" else 0,
                "age": age,
                "height_cm": round(height, 2),
                "weight_kg": round(weight, 2),
                "experience_years": experience,
                "training_level": training_level,
                "ability": round(ability, 5),
            })
        return athletes

    def _assign_splits(self, athlete_ids: List[str]) -> Dict[str, str]:
        shuffled = list(athlete_ids)
        self.rng.shuffle(shuffled)
        n = len(shuffled)
        n_train = max(1, int(round(n * self.config.train_ratio)))
        n_val = max(1, int(round(n * self.config.val_ratio)))
        if n_train + n_val >= n:
            n_train = n - 2
            n_val = 1
        return {
            athlete_id: "train" if index < n_train else "val" if index < n_train + n_val else "test"
            for index, athlete_id in enumerate(shuffled)
        }

    def _generate_trial(
        self,
        athlete: Dict,
        trial_index: int,
        split: str,
    ) -> tuple[Dict, List[Dict]]:
        ability = athlete["ability"]
        experience = athlete["experience_years"]
        training_level = athlete["training_level"]
        is_outlier = bool(self.rng.random() < self.config.outlier_rate)
        noise_multiplier = 2.5 if is_outlier else 1.0
        noise = self.config.noise_level * noise_multiplier

        time_10m = float(np.clip(
            2.38
            - ability * 0.12
            - experience * 0.018
            - (training_level - 3) * 0.045
            + self.rng.normal(0, 0.08 + noise * 0.08),
            1.65,
            3.00,
        ))
        average_speed = self.config.sprint_distance_m / time_10m
        max_speed = average_speed * float(np.clip(1.18 + training_level * 0.035 + self.rng.normal(0, 0.03), 1.10, 1.42))
        cadence = float(np.clip(
            2.75 + (training_level - 3) * 0.10 + (athlete["height_cm"] - 170.0) * 0.002 + self.rng.normal(0, 0.12 + noise * 0.12),
            2.20,
            4.70,
        ))
        stride_length = average_speed / cadence * float(np.clip(1.0 + self.rng.normal(0, noise * 0.06), 0.85, 1.15))

        knee_angle = float(np.clip(103.0 - ability * 2.5 + self.rng.normal(0, 7.0 + noise * 8.0), 75.0, 140.0))
        hip_angle = float(np.clip(80.0 - ability * 2.0 + self.rng.normal(0, 8.0 + noise * 8.0), 42.0, 120.0))
        trunk_angle = float(np.clip(25.0 + (3.0 - training_level) * 1.8 + self.rng.normal(0, 3.0 + noise * 4.0), 10.0, 48.0))
        knee_symmetry = float(abs(self.rng.normal(0.0, 3.0 + noise * 12.0)))
        hip_symmetry = float(abs(self.rng.normal(0.0, 2.5 + noise * 10.0)))
        posture_score = float(np.clip(
            100.0
            - abs(knee_angle - 95.0) * 0.30
            - abs(hip_angle - 65.0) * 0.25
            - abs(trunk_angle - 25.0) * 0.35
            - (knee_symmetry + hip_symmetry) * 0.45
            + self.rng.normal(0, 2.0 + noise * 5.0),
            35.0,
            100.0,
        ))
        reaction_time = float(np.clip(
            0.18 + (100.0 - posture_score) * 0.0015 + self.rng.normal(0.0, 0.025 + noise * 0.02),
            0.12,
            0.45,
        ))

        if time_10m <= 2.15 and posture_score >= 65.0:
            quality_class = "buena"
        elif time_10m <= 2.45 and posture_score >= 50.0:
            quality_class = "regular"
        else:
            quality_class = "mala"

        confidence_base = float(np.clip(0.94 - noise * 0.18 - (0.04 if is_outlier else 0.0) + self.rng.normal(0, 0.02), 0.55, 0.995))
        quality_flag = "ok"
        if is_outlier:
            quality_flag = "high_noise" if self.rng.random() < 0.6 else "low_visibility"

        athlete_id = athlete["athlete_id"]
        trial_id = f"{athlete_id}_T{trial_index + 1:02d}"
        trial = {
            "trial_id": trial_id,
            "athlete_id": athlete_id,
            "session_id": f"SYN_S{athlete_id.split('_A')[1]}",
            "split": split,
            "trial_index": trial_index + 1,
            "sex": athlete["sex"],
            "sex_encoded": athlete["sex_encoded"],
            "age": athlete["age"],
            "height_cm": athlete["height_cm"],
            "weight_kg": athlete["weight_kg"],
            "experience_years": athlete["experience_years"],
            "training_level": athlete["training_level"],
            "camera_height_m": round(float(self.rng.uniform(4.0, 12.0)), 2),
            "camera_distance_m": round(float(self.rng.uniform(8.0, 22.0)), 2),
            "camera_angle_deg": round(float(self.rng.uniform(0.0, 45.0)), 2),
            "fps": self.config.fps,
            "lighting_lux": round(float(self.rng.uniform(250.0, 1200.0)), 1),
            "signal_quality": round(float(np.clip(self.rng.normal(0.86, 0.08) - noise * 0.15, 0.35, 1.0)), 4),
            "visibility_ratio": round(float(np.clip(self.rng.normal(0.94, 0.05) - noise * 0.18, 0.35, 1.0)), 4),
            "tracking_confidence": round(float(np.clip(self.rng.normal(confidence_base, 0.025), 0.35, 0.999)), 4),
            "pose_confidence": round(float(np.clip(self.rng.normal(confidence_base - 0.02, 0.03), 0.30, 0.999)), 4),
            "avg_knee_angle": round(knee_angle, 3),
            "avg_hip_angle": round(hip_angle, 3),
            "trunk_angle": round(trunk_angle, 3),
            "knee_symmetry": round(knee_symmetry, 3),
            "hip_symmetry": round(hip_symmetry, 3),
            "posture_score": round(posture_score, 3),
            "reaction_time_s": round(reaction_time, 4),
            "time_10m_s": round(time_10m, 4),
            "average_speed_ms": round(average_speed, 4),
            "max_speed_ms": round(max_speed, 4),
            "stride_length_m": round(stride_length, 4),
            "cadence_steps_s": round(cadence, 4),
            "quality_class": quality_class,
            "quality_flag": quality_flag,
            "is_outlier": int(is_outlier),
        }
        return trial, self._generate_trial_frames(trial, confidence_base, noise)

    def _generate_trial_frames(
        self,
        trial: Dict,
        confidence_base: float,
        noise: float,
    ) -> List[Dict]:
        duration = float(trial["time_10m_s"])
        n_frames = max(6, int(round(duration * self.config.fps)))
        if self.config.max_frames_per_trial is not None:
            n_frames = min(n_frames, self.config.max_frames_per_trial)
        u = np.linspace(0.0, 1.0, n_frames)
        progress_curve = 0.55 * u + 0.45 * (1.0 - np.exp(-2.0 * u)) / (1.0 - np.exp(-2.0))
        progress = self.config.sprint_distance_m * progress_curve
        average_speed = float(trial["average_speed_ms"])
        max_speed = float(trial["max_speed_ms"])
        speed_factor = 0.55 + 0.45 * (1.0 - np.exp(-2.0 * u)) / (1.0 - np.exp(-2.0))
        speed = average_speed * speed_factor + self.rng.normal(0, 0.015 + noise * 0.05, n_frames)
        speed = np.clip(speed, 0.2, max_speed)
        cadence = np.clip(
            float(trial["cadence_steps_s"]) * (1.0 + 0.035 * np.sin(2.0 * np.pi * 2.2 * u)) + self.rng.normal(0, noise * 0.05, n_frames),
            1.5,
            6.0,
        )
        stride = speed / cadence
        posture = np.clip(
            float(trial["posture_score"]) - 2.5 * u + self.rng.normal(0, 0.8 + noise * 2.0, n_frames),
            0.0,
            100.0,
        )
        knee = np.clip(
            float(trial["avg_knee_angle"]) + 3.0 * np.sin(2.0 * np.pi * 1.8 * u) + self.rng.normal(0, noise * 3.0, n_frames),
            50.0,
            170.0,
        )
        hip = np.clip(
            float(trial["avg_hip_angle"]) + 2.0 * np.sin(2.0 * np.pi * 1.8 * u + 0.8) + self.rng.normal(0, noise * 3.0, n_frames),
            20.0,
            150.0,
        )
        trunk = np.clip(
            float(trial["trunk_angle"]) - 2.0 * u + self.rng.normal(0, noise * 2.0, n_frames),
            0.0,
            70.0,
        )
        hip_x = progress + self.rng.normal(0, 0.01, n_frames)
        hip_y = 0.90 + 0.06 * np.sin(2.0 * np.pi * 1.8 * u) + self.rng.normal(0, 0.01, n_frames)
        pose_confidence = np.clip(
            confidence_base + self.rng.normal(0, 0.025, n_frames) - noise * 0.04,
            0.25,
            0.999,
        )
        tracking_confidence = np.clip(
            confidence_base + 0.01 + self.rng.normal(0, 0.02, n_frames) - noise * 0.03,
            0.25,
            0.999,
        )

        rows = []
        for index in range(n_frames):
            phase = "acceleration" if u[index] < 0.35 else "steady" if u[index] < 0.8 else "deceleration"
            rows.append({
                "trial_id": trial["trial_id"],
                "athlete_id": trial["athlete_id"],
                "split": trial["split"],
                "frame_index": index,
                "time_s": round(float(u[index] * duration), 4),
                "progress_m": round(float(progress[index]), 4),
                "speed_ms": round(float(speed[index]), 4),
                "stride_length_m": round(float(stride[index]), 4),
                "cadence_steps_s": round(float(cadence[index]), 4),
                "hip_x_m": round(float(hip_x[index]), 4),
                "hip_y_m": round(float(hip_y[index]), 4),
                "knee_angle_deg": round(float(knee[index]), 3),
                "hip_angle_deg": round(float(hip[index]), 3),
                "trunk_angle_deg": round(float(trunk[index]), 3),
                "knee_symmetry_deg": trial["knee_symmetry"],
                "hip_symmetry_deg": trial["hip_symmetry"],
                "posture_score": round(float(posture[index]), 3),
                "pose_confidence": round(float(pose_confidence[index]), 4),
                "tracking_confidence": round(float(tracking_confidence[index]), 4),
                "phase": phase,
            })
        return rows

    @staticmethod
    def _write_csv(path: Path, rows: List[Dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        fieldnames = list(rows[0].keys())
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
