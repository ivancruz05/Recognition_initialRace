"""Tests for validation against manual ground truth."""

import pytest

from detection.metrics.validation import ValidationAnalyzer


def test_validation_computes_errors():
    analyzer = ValidationAnalyzer()
    report = analyzer.compare(
        automatic={"velocidad": 8.5, "cadencia": 4.2},
        manual={"velocidad": 8.0, "cadencia": 4.0},
        athlete_id="P01",
    )
    assert report.athlete_id == "P01"
    assert report.status == "ACCEPTABLE"
    assert report.mape_percent == pytest.approx(5.625)

    by_var = {v.variable: v for v in report.per_variable}
    assert by_var["velocidad"].absolute_error == pytest.approx(0.5)
    assert by_var["velocidad"].relative_error_percent == pytest.approx(6.25)
    assert by_var["cadencia"].relative_error_percent == pytest.approx(5.0)


def test_validation_missing_variable():
    analyzer = ValidationAnalyzer(variables=["velocidad"])
    report = analyzer.compare(
        automatic={},
        manual={"velocidad": 8.0},
        athlete_id="P02",
    )
    assert report.status == "INSUFFICIENT_DATA"
    assert report.per_variable[0].absolute_error is None


def test_validation_zero_manual():
    analyzer = ValidationAnalyzer(variables=["velocidad"])
    report = analyzer.compare(
        automatic={"velocidad": 0.5},
        manual={"velocidad": 0.0},
        athlete_id="P03",
    )
    assert report.per_variable[0].relative_error_percent is None
    assert report.per_variable[0].absolute_error == pytest.approx(0.5)
