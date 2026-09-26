"""Validation of automatic metrics against a manual ground-truth reference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class VariableValidation:
    """Validation result for a single numeric variable."""
    variable: str
    automatic: Optional[float]
    manual: Optional[float]
    absolute_error: Optional[float]
    relative_error_percent: Optional[float]


@dataclass
class ValidationReport:
    """Aggregated validation report for one athlete/session."""
    athlete_id: str
    per_variable: List[VariableValidation] = field(default_factory=list)
    mape_percent: Optional[float] = None
    status: str = "PENDING"
    notes: List[str] = field(default_factory=list)


class ValidationAnalyzer:
    """Compare automatically computed variables against manual ground truth."""

    # Suggested ISO/IEC 25010 inspired accuracy bands for sprint metrics.
    BANDS = {
        "EXCELLENT": 5.0,
        "ACCEPTABLE": 10.0,
        "LIMIT": 15.0,
    }

    def __init__(self, variables: Optional[List[str]] = None):
        """
        Args:
            variables: list of variable names to validate. Defaults to the
                four variables required by the project document.
        """
        self.variables = variables or [
            "postura",
            "velocidad",
            "longitud_zancada",
            "cadencia",
        ]

    def compare(
        self,
        automatic: Dict[str, float],
        manual: Dict[str, float],
        athlete_id: str = "unknown",
    ) -> ValidationReport:
        """Compute absolute and relative errors per variable.

        Args:
            automatic: dict variable_name -> numeric value from the software.
            manual: dict variable_name -> numeric value from manual annotation.
            athlete_id: identifier of the athlete/session.

        Returns:
            ValidationReport with per-variable errors and aggregated MAPE.
        """
        per_variable: List[VariableValidation] = []
        relative_errors: List[float] = []
        notes: List[str] = []

        for var in self.variables:
            auto_val = automatic.get(var)
            man_val = manual.get(var)

            if auto_val is None or man_val is None:
                per_variable.append(VariableValidation(
                    variable=var,
                    automatic=auto_val,
                    manual=man_val,
                    absolute_error=None,
                    relative_error_percent=None,
                ))
                notes.append(f"{var}: falta valor automático o manual")
                continue

            abs_err = abs(auto_val - man_val)
            rel_err = (abs_err / abs(man_val) * 100.0) if man_val != 0 else None

            per_variable.append(VariableValidation(
                variable=var,
                automatic=float(auto_val),
                manual=float(man_val),
                absolute_error=float(abs_err),
                relative_error_percent=float(rel_err) if rel_err is not None else None,
            ))

            if rel_err is not None:
                relative_errors.append(rel_err)

        mape = sum(relative_errors) / len(relative_errors) if relative_errors else None
        status = self._status_from_mape(mape)

        return ValidationReport(
            athlete_id=athlete_id,
            per_variable=per_variable,
            mape_percent=mape,
            status=status,
            notes=notes,
        )

    def _status_from_mape(self, mape: Optional[float]) -> str:
        if mape is None:
            return "INSUFFICIENT_DATA"
        if mape <= self.BANDS["EXCELLENT"]:
            return "EXCELLENT"
        if mape <= self.BANDS["ACCEPTABLE"]:
            return "ACCEPTABLE"
        if mape <= self.BANDS["LIMIT"]:
            return "LIMIT"
        return "UNACCEPTABLE"

    @staticmethod
    def report_to_dict(report: ValidationReport) -> Dict:
        """Serialize a validation report to a plain dict."""
        return {
            "athlete_id": report.athlete_id,
            "status": report.status,
            "mape_percent": report.mape_percent,
            "per_variable": [
                {
                    "variable": v.variable,
                    "automatic": v.automatic,
                    "manual": v.manual,
                    "absolute_error": v.absolute_error,
                    "relative_error_percent": v.relative_error_percent,
                }
                for v in report.per_variable
            ],
            "notes": report.notes,
        }
