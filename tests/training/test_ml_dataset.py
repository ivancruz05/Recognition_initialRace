"""Tests for synthetic dataset generation and baseline training."""

import json
from pathlib import Path

import pandas as pd

from training.synthetic import SyntheticDatasetConfig, SyntheticDatasetGenerator
from training.trainer import load_model, train_baseline


def _generate(tmp_path: Path, n_athletes: int = 40):
    config = SyntheticDatasetConfig(
        n_athletes=n_athletes,
        min_trials=2,
        max_trials=2,
        fps=5,
        max_frames_per_trial=10,
        seed=123,
    )
    return SyntheticDatasetGenerator(config).generate(tmp_path)


def test_synthetic_dataset_creates_consistent_tables(tmp_path):
    summary = _generate(tmp_path)

    assert summary.athletes == 40
    assert summary.trials == 80
    assert summary.frames == 800
    assert set(summary.files) == {"athletes", "trials", "frames", "splits", "metadata"}

    trials = pd.read_csv(summary.files["trials"])
    frames = pd.read_csv(summary.files["frames"])
    metadata = json.loads(Path(summary.files["metadata"]).read_text(encoding="utf-8"))

    assert len(trials) == summary.trials
    assert len(frames) == summary.frames
    assert metadata["synthetic"] is True
    assert metadata["contains_personal_data"] is False
    assert {"time_10m_s", "quality_class", "posture_score"}.issubset(trials.columns)
    assert trials["trial_id"].is_unique
    assert set(trials["split"]) == {"train", "val", "test"}
    assert trials["time_10m_s"].between(1.65, 3.0).all()
    assert trials["quality_class"].isin({"buena", "regular", "mala"}).all()
    assert frames["progress_m"].between(0.0, 10.0).all()


def test_synthetic_split_is_athlete_level(tmp_path):
    summary = _generate(tmp_path)
    trials = pd.read_csv(summary.files["trials"])

    athlete_splits = trials.groupby("athlete_id")["split"].nunique()
    assert (athlete_splits == 1).all()

    split_athletes = trials.groupby("split")["athlete_id"].apply(set)
    assert not (split_athletes["train"] & split_athletes["test"])
    assert not (split_athletes["train"] & split_athletes["val"])
    assert not (split_athletes["val"] & split_athletes["test"])


def test_baseline_training_writes_model_and_metrics(tmp_path):
    summary = _generate(tmp_path)
    model_dir = tmp_path / "model"
    metrics = train_baseline(
        summary.files["trials"],
        model_dir,
        n_estimators=10,
        seed=7,
    )

    assert metrics["model"] == "random_forest"
    assert set(metrics["regression"]) == {"mae_s", "rmse_s", "r2"}
    assert (model_dir / "model.joblib").exists()
    assert (model_dir / "metrics.json").exists()
    assert (model_dir / "feature_importance.csv").exists()
    assert (model_dir / "test_predictions.csv").exists()

    bundle = load_model(model_dir / "model.joblib")
    assert bundle.is_fitted
    assert bundle.config.regression_target == "time_10m_s"
    assert "posture_score" in bundle.config.feature_columns
