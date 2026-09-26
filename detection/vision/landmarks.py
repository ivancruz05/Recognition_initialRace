"""Constantes de landmarks del esqueleto humano (MediaPipe Pose, 33 puntos).

Cada landmark tiene [x, y, z, visibility] normalizados (0-1).
"""

NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_HEEL = 29
RIGHT_HEEL = 30
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32

NUM_LANDMARKS = 33

LANDMARKS = {
    "nose": NOSE,
    "left_shoulder": LEFT_SHOULDER,
    "right_shoulder": RIGHT_SHOULDER,
    "left_elbow": LEFT_ELBOW,
    "right_elbow": RIGHT_ELBOW,
    "left_wrist": LEFT_WRIST,
    "right_wrist": RIGHT_WRIST,
    "left_hip": LEFT_HIP,
    "right_hip": RIGHT_HIP,
    "left_knee": LEFT_KNEE,
    "right_knee": RIGHT_KNEE,
    "left_ankle": LEFT_ANKLE,
    "right_ankle": RIGHT_ANKLE,
    "left_heel": LEFT_HEEL,
    "right_heel": RIGHT_HEEL,
    "left_foot_index": LEFT_FOOT_INDEX,
    "right_foot_index": RIGHT_FOOT_INDEX,
}

CONNECTIONS = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (RIGHT_HIP, RIGHT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_KNEE, RIGHT_ANKLE),
    (LEFT_ANKLE, LEFT_HEEL),
    (RIGHT_ANKLE, RIGHT_HEEL),
    (LEFT_HEEL, LEFT_FOOT_INDEX),
    (RIGHT_HEEL, RIGHT_FOOT_INDEX),
]

KEY_POINTS = [
    ("Nose", NOSE),
    ("L_Shoulder", LEFT_SHOULDER),
    ("R_Shoulder", RIGHT_SHOULDER),
    ("L_Elbow", LEFT_ELBOW),
    ("R_Elbow", RIGHT_ELBOW),
    ("L_Hip", LEFT_HIP),
    ("R_Hip", RIGHT_HIP),
    ("L_Knee", LEFT_KNEE),
    ("R_Knee", RIGHT_KNEE),
    ("L_Ankle", LEFT_ANKLE),
    ("R_Ankle", RIGHT_ANKLE),
]

GROUP_INDICES = {
    "face": list(range(11)),
    "torso": list(range(11, 25)),
    "left_leg": [LEFT_HIP, LEFT_KNEE, LEFT_ANKLE, LEFT_HEEL, LEFT_FOOT_INDEX],
    "right_leg": [RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE, RIGHT_HEEL, RIGHT_FOOT_INDEX],
}

GROUP_COLORS = {
    "face": (0, 255, 255),
    "torso": (0, 200, 0),
    "left_leg": (255, 100, 0),
    "right_leg": (0, 100, 255),
}