"""Architecture guard: module boundaries must not regress.

These are cheap import-level assertions. They encode the decisions behind the
modular split so a later import "just for convenience" fails loudly in CI
instead of silently coupling metrics to OpenCV.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTION = REPO_ROOT / "detection"


def _imported_modules(package_dir: Path) -> set[str]:
    """Every first-party module imported anywhere under package_dir."""
    found: set[str] = set()
    for path in package_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
            elif isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
    return found


def test_metrics_does_not_depend_on_vision():
    """detection/metrics is pure math: it must not import the cv2 adapters."""
    offenders = sorted(
        m for m in _imported_modules(DETECTION / "metrics") if m.startswith("detection.vision")
    )
    assert offenders == [], f"detection/metrics must stay I/O-free, found: {offenders}"


@pytest.mark.parametrize(
    "module_name",
    ["detection"],
)
def test_public_modules_import_cleanly(module_name):
    """Importing a package must not require the other one."""
    __import__(module_name)
