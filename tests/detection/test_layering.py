"""Architecture guards for the recognition MVP's production layers."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTION = REPO_ROOT / "detection"
STDLIB_MODULES = {
    "__future__",
    "collections",
    "dataclasses",
    "enum",
    "math",
    "threading",
    "types",
    "typing",
}


def _imports(package_dir: Path) -> set[str]:
    """Return imported module names from all Python files below a layer."""
    found: set[str] = set()
    paths = [package_dir] if package_dir.is_file() else package_dir.rglob("*.py")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
            elif isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
    return found


def _third_party_imports(package_dir: Path) -> set[str]:
    return {
        name
        for name in _imports(package_dir)
        if name.split(".", 1)[0] not in STDLIB_MODULES
        and name.split(".", 1)[0] != "detection"
    }


def test_domain_imports_only_domain_modules_and_python_standard_library():
    offenders = sorted(_third_party_imports(DETECTION / "domain"))

    assert offenders == [], f"domain must be dependency-free, found: {offenders}"
    first_party = sorted(
        name
        for name in _imports(DETECTION / "domain")
        if name.startswith("detection.") and not name.startswith("detection.domain")
    )
    assert first_party == [], f"domain must not import outer layers: {first_party}"


def test_application_imports_only_domain_modules_and_standard_library():
    imports = _imports(DETECTION / "application")
    offenders = sorted(
        name
        for name in imports
        if name.split(".", 1)[0] not in STDLIB_MODULES
        and not name.startswith(("detection.domain", "detection.application"))
    )

    assert offenders == [], f"application imports outside domain: {offenders}"


def test_infrastructure_and_cli_follow_the_recognition_layer_boundaries():
    infrastructure_imports = _imports(DETECTION / "infrastructure")
    infrastructure_offenders = sorted(
        name
        for name in infrastructure_imports
        if name.startswith("detection.")
        and not name.startswith(("detection.domain", "detection.infrastructure"))
    )
    assert infrastructure_offenders == [], (
        "infrastructure may depend on domain and external frameworks, but not "
        f"application/legacy modules: {infrastructure_offenders}"
    )

    cli_imports = _imports(DETECTION / "local_cli.py")
    cli_first_party = {
        name for name in cli_imports if name.startswith("detection.")
    }
    assert any(name.startswith("detection.application") for name in cli_first_party)
    assert any(name.startswith("detection.infrastructure") for name in cli_first_party)
    assert not any(name.startswith("detection.vision") for name in cli_first_party)


@pytest.mark.parametrize("module_name", ["detection", "detection.domain"])
def test_public_packages_import_cleanly(module_name):
    __import__(module_name)


def test_importing_domain_does_not_load_vision_or_external_frameworks():
    script = """
import sys
import detection.domain

forbidden = ('detection.vision', 'cv2', 'mediapipe', 'numpy', 'click')
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden)
)
assert not loaded, 'unexpected imports: {}'.format(loaded)
"""
    import subprocess

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
