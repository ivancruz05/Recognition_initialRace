"""Reusable machine-learning base for sprint biomechanics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

from training.features import DEFAULT_FEATURE_COLUMNS, as_feature_frame, validate_feature_columns


@dataclass(frozen=True)
class SprintMLConfig:
    """Configuration shared by regression and classification models."""

    regression_target: str = "time_10m_s"
    classification_target: str = "quality_class"
    feature_columns: Tuple[str, ...] = tuple(DEFAULT_FEATURE_COLUMNS)
    n_estimators: int = 200
    min_samples_leaf: int = 2
    random_state: int = 42
    imputer_strategy: str = "median"
    train_split: str = "train"
    test_split: str = "test"


@dataclass
class SprintMLModel:
    """Train, predict and persist a pair of Random Forest baselines.

    The class is the extension point for replacing Random Forest with another
    estimator while keeping the same feature schema and prediction interface.
    """

    config: SprintMLConfig = field(default_factory=SprintMLConfig)
    regressor: Optional[Pipeline] = None
    classifier: Optional[Pipeline] = None
    classes: List[str] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)

    @property
    def is_fitted(self) -> bool:
        return self.regressor is not None

    def fit(
        self,
        trials: pd.DataFrame,
        include_outliers: bool = False,
    ) -> "SprintMLModel":
        """Fit the regression and optional classification pipelines."""
        self._validate_training_frame(trials)
        data = trials.copy()
        if "quality_flag" in data.columns and not include_outliers:
            data = data[data["quality_flag"] == "ok"].copy()
        data = data.dropna(subset=list(self.config.feature_columns) + [self.config.regression_target]).copy()

        train = data[data["split"] == self.config.train_split].copy()
        test = data[data["split"] == self.config.test_split].copy()
        if train.empty or test.empty:
            raise ValueError("Dataset must contain non-empty train and test splits")
        self._assert_athlete_disjoint(train, test)

        x_train = as_feature_frame(train, self.config.feature_columns)
        x_test = as_feature_frame(test, self.config.feature_columns)
        y_train = train[self.config.regression_target].astype(float)
        y_test = test[self.config.regression_target].astype(float)

        self.regressor = self._make_regressor()
        self.regressor.fit(x_train, y_train)
        regression_predictions = self.regressor.predict(x_test)
        regression_metrics = {
            "mae_s": float(mean_absolute_error(y_test, regression_predictions)),
            "rmse_s": float(np.sqrt(mean_squared_error(y_test, regression_predictions))),
            "r2": float(r2_score(y_test, regression_predictions)),
        }

        self.classifier = None
        self.classes = []
        classification_metrics: Optional[Dict] = None
        if self.config.classification_target in data.columns:
            train_labels = train[self.config.classification_target].astype(str)
            test_labels = test[self.config.classification_target].astype(str)
            if train_labels.nunique() >= 2:
                self.classifier = self._make_classifier()
                self.classifier.fit(x_train, train_labels)
                self.classes = sorted(self.classifier.named_steps["forest"].classes_.tolist())
                classification_predictions = self.classifier.predict(x_test)
                classification_metrics = {
                    "accuracy": float(accuracy_score(test_labels, classification_predictions)),
                    "macro_f1": float(
                        f1_score(
                            test_labels,
                            classification_predictions,
                            average="macro",
                            zero_division=0,
                        )
                    ),
                    "classes": self.classes,
                }

        self.metrics = {
            "model": "random_forest",
            "features": list(self.config.feature_columns),
            "regression_target": self.config.regression_target,
            "classification_target": self.config.classification_target,
            "rows": {
                "total": int(len(data)),
                "train": int(len(train)),
                "test": int(len(test)),
            },
            "athletes": {
                "train": int(train["athlete_id"].nunique()),
                "test": int(test["athlete_id"].nunique()),
            },
            "regression": regression_metrics,
            "classification": classification_metrics,
        }
        return self

    def predict(self, data: pd.DataFrame | Dict) -> pd.DataFrame:
        """Predict sprint time and, when available, quality class."""
        if not self.is_fitted or self.regressor is None:
            raise RuntimeError("The model must be fitted before prediction")
        features = as_feature_frame(data, self.config.feature_columns)
        result = pd.DataFrame(index=features.index)
        result["predicted_time_10m_s"] = self.regressor.predict(features)
        if self.classifier is not None:
            result["predicted_quality_class"] = self.classifier.predict(features)
            probabilities = self.classifier.predict_proba(features)
            for index, class_name in enumerate(self.classes):
                result[f"probability_{class_name}"] = probabilities[:, index]
        return result

    def predict_one(self, features: Dict) -> Dict:
        """Predict one trial and return a plain dictionary."""
        return self.predict(features).iloc[0].to_dict()

    def feature_importances(self) -> pd.DataFrame:
        """Return feature importance for both available targets."""
        if not self.is_fitted or self.regressor is None:
            raise RuntimeError("The model must be fitted before feature importances are available")
        regression_importance = self.regressor.named_steps["forest"].feature_importances_
        if self.classifier is not None:
            classification_importance = self.classifier.named_steps["forest"].feature_importances_
        else:
            classification_importance = np.zeros(len(self.config.feature_columns))
        return pd.DataFrame({
            "feature": list(self.config.feature_columns),
            "regression_importance": regression_importance,
            "classification_importance": classification_importance,
        }).sort_values("regression_importance", ascending=False, ignore_index=True)

    def save(self, path: str | Path) -> None:
        """Persist the complete model bundle."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str | Path) -> "SprintMLModel":
        """Load a model bundle created by :meth:`save`."""
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError("The file does not contain a SprintMLModel")
        return model

    def _make_regressor(self) -> Pipeline:
        return Pipeline([
            ("imputer", SimpleImputer(strategy=self.config.imputer_strategy)),
            ("forest", RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state,
                n_jobs=-1,
            )),
        ])

    def _make_classifier(self) -> Pipeline:
        return Pipeline([
            ("imputer", SimpleImputer(strategy=self.config.imputer_strategy)),
            ("forest", RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state,
                n_jobs=-1,
            )),
        ])

    @staticmethod
    def _validate_training_frame(trials: pd.DataFrame) -> None:
        if not isinstance(trials, pd.DataFrame):
            raise TypeError("trials must be a pandas DataFrame")
        required = {"trial_id", "athlete_id", "split", "time_10m_s"}
        missing = sorted(required - set(trials.columns))
        if missing:
            raise ValueError(f"Missing training columns: {', '.join(missing)}")
        validate_feature_columns(trials, DEFAULT_FEATURE_COLUMNS)

    @staticmethod
    def _assert_athlete_disjoint(train: pd.DataFrame, test: pd.DataFrame) -> None:
        overlap = set(train["athlete_id"]) & set(test["athlete_id"])
        if overlap:
            raise ValueError(f"Athlete leakage detected between train and test: {sorted(overlap)[:5]}")
