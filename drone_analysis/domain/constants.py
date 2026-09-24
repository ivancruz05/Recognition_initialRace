"""Domain constants - Landmark indices, optimal values, body proportions."""

from typing import Dict, List, Tuple

# Landmark indices (MediaPipe Pose)
LANDMARKS = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}

NUM_LANDMARKS = 33

# Skeletal connections for drawing
CONNECTIONS: List[Tuple[int, int]] = [
    (11, 12),  # shoulders
    (11, 13), (12, 14),  # upper arms
    (13, 15), (14, 16),  # forearms
    (11, 23), (12, 24),  # torso
    (23, 24),  # hips
    (23, 25), (24, 26),  # upper legs
    (25, 27), (26, 28),  # lower legs
    (27, 29), (28, 30),  # ankles
    (29, 31), (30, 32),  # feet
]

# Optimal sprint start angles (from literature)
# References:
# - Coh et al. (2017) - Biomechanical analysis of block start
# - Debaere et al. (2013) - Knee angles during sprint start
# - Vanrenterghem et al. (2017) - Hip angles in sprint start
# - Harland & Steele (1997) - Anthropometric and strength values
# - Mero et al. (1992) - Kinematic and kinetic analysis
# - Cavedon et al. (2019) - Sprint start biomechanics

OPTIMAL_ANGLES: Dict[str, Tuple[float, float]] = {
    # Front leg angles (more flexed)
    "front_knee": (80, 100),      # Coh et al. 2017, Debaere et al. 2013
    "front_hip": (45, 70),        # Coh et al. 2017, Vanrenterghem et al. 2017
    "front_ankle": (70, 90),      # Cavedon et al. 2019
    
    # Rear leg angles (more extended)
    "rear_knee": (110, 150),      # Coh et al. 2017
    "rear_hip": (85, 115),        # Coh et al. 2017
    "rear_ankle": (90, 110),      # Cavedon et al. 2019
    
    # Trunk angle (from horizontal)
    "trunk": (15, 45),            # Harland & Steele 1997, Mero et al. 1992
    
    # Legacy keys for backward compatibility
    "knee": (90, 120),
    "hip": (45, 90),
}

# Body proportions (Mann 2011)
BODY_PROPORTIONS: Dict[str, float] = {
    "leg_ratio": 0.47,      # leg length / height
    "arm_ratio": 0.44,      # arm length / height
    "torso_ratio": 0.30,    # torso length / height
    "foot_ratio": 0.15,     # foot length / height
    "shoulder_ratio": 0.26, # shoulder width / height
}

# Color schemes for visualization
GROUP_COLORS = {
    "face": (0, 255, 255),
    "torso": (0, 200, 0),
    "left_leg": (255, 100, 0),
    "right_leg": (0, 100, 255),
}

# Quality score thresholds
QUALITY_THRESHOLDS = {
    "excellent": 8.0,
    "good": 6.0,
    "average": 4.0,
    "poor": 2.0,
}
