"""Tests for the reusable sprint ML model."""

import numpy as np
import pandas as pd
import pytest

from training.model import SprintMLConfig, SprintMLModel
from training.synthetic import SyntheticDatasetConfig, SyntheticDatasetGenerator


def _fit_model(tmp_path):
    summary = SyntheticDatasetGenerator(SyntheticDatasetConfig(
        n_athletes=24,
        min_trials=2,
        max_trials=2,
        fps=5,
        max_frames_per_trial=10,
        seed=321,
    )).generate(tmp_path)
    trials = pd.read_csv(summary.files["trials"])
    model = SprintMLModel(SprintMLConfig(n_estimators=10, random_state=11))
    model.fit(trials)
    return model, trials


def test_model_predicts_and_handles_missing_features(tmp_path):
    model, trials = _fit_model(tmp_path)
    row = trials.iloc[0].to_dict()
    row["pose_confidence"] = np.nan

    prediction = model.predict_one(row)

    assert model.is_fitted
    assert "predicted_time_10m_s" in prediction
    assert "predicted_quality_class" in prediction
    assert np.isfinite(prediction["predicted_time_10m_s"])


def test_model_roundtrip_preserves_predictions(tmp_path):
    model, trials = _fit_model(tmp_path)
    row = trials.iloc[1].to_dict()
    before = model.predict_one(row)["predicted_time_10m_s"]
    path = tmp_path / "model.joblib"
    model.save(path)
    loaded = SprintMLModel.load(path)
    after = loaded.predict_one(row)["predicted_time_10m_s"]
    importance = loaded.feature_importances()

    assert before == after
    assert len(importance) == len(loaded.config.feature_columns)
    assert importance["regression_importance"].sum() == pytest.approx(1.0)
