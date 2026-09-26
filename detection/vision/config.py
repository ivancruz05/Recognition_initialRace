"""Infrastructure configuration."""

from pathlib import Path
from typing import Optional

from dataclasses import dataclass, field


@dataclass
class Settings:
    """Project settings."""

    # Paths
    root_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    data_dir: Optional[Path] = None
    models_dir: Optional[Path] = None

    # Pose detection
    model_complexity: int = 2
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    num_landmarks: int = 33

    # Depth
    max_depth_meters: float = 10.0
    depth_width: int = 256
    depth_height: int = 192

    # Body measurement
    visibility_threshold: float = 0.5

    def __post_init__(self):
        if self.data_dir is None:
            self.data_dir = self.root_dir / "data"
        if self.models_dir is None:
            self.models_dir = self.root_dir / "models"

    def ensure_dirs(self) -> None:
        """Create required directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
