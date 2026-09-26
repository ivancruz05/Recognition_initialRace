"""Constants for pose validation and view detection."""

from __future__ import annotations

# Visibility threshold for a landmark to be considered reliable.
VISIBILITY_THRESHOLD = 0.5

# Minimum number of key landmarks that must be visible for a valid pose.
MIN_KEY_LANDMARKS_VISIBLE = 6

# Maximum lateral shoulder tilt (normalized Y difference) allowed.
MAX_LATERAL_TILT = 0.08

# Minimum number of valid frames required to generate a report.
MIN_VALID_FRAMES = 5

# View detection thresholds.
VIEW_FRONT_SHOULDER_THRESHOLD = 0.12
VIEW_PROFILE_Z_RATIO = 1.5
VIEW_MIN_VISIBILITY = 0.5

# Default capture settings.
DEFAULT_FRAME_WIDTH = 640
DEFAULT_FRAME_HEIGHT = 480
DEFAULT_DEPTH_WIDTH = 256
DEFAULT_DEPTH_HEIGHT = 192

MAX_DEPTH_METERS = 10.0
LOW_RES_THRESHOLD = 1920
MAX_CAMERA_INDEX = 4
