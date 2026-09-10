"""Configuración global del proyecto."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"
MODELS_DIR = ROOT_DIR / "models"

VISIBILITY_THRESHOLD = 0.5
LOW_RES_THRESHOLD = 1920
MAX_CAMERA_INDEX = 4

DEFAULT_FRAME_WIDTH = 640
DEFAULT_FRAME_HEIGHT = 480
DEFAULT_DEPTH_WIDTH = 256
DEFAULT_DEPTH_HEIGHT = 192

MAX_DEPTH_METERS = 10.0


def ensure_dir(path: Path) -> Path:
    """Crea el directorio si no existe y lo devuelve."""
    path.mkdir(parents=True, exist_ok=True)
    return path