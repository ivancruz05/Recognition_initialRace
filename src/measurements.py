"""Estimación de distancias y ángulos corporales a partir de landmarks 2D."""

import numpy as np

from src import landmarks as lm
from src.config import VISIBILITY_THRESHOLD

# Distancias de referencia del cuerpo humano en metros (promedios).
REFERENCE_DISTANCES = {
    "shoulder_width": 0.40,
    "hip_width": 0.35,
    "upper_arm": 0.30,
    "forearm": 0.25,
    "thigh": 0.45,
    "shank": 0.40,
    "torso_length": 0.50,
}

# Pares de landmarks y su distancia de referencia asociada.
DISTANCE_PAIRS = {
    "shoulder_width": (lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER),
    "hip_width": (lm.LEFT_HIP, lm.RIGHT_HIP),
    "left_thigh": (lm.LEFT_HIP, lm.LEFT_KNEE),
    "right_thigh": (lm.RIGHT_HIP, lm.RIGHT_KNEE),
    "left_shank": (lm.LEFT_KNEE, lm.LEFT_ANKLE),
    "right_shank": (lm.RIGHT_KNEE, lm.RIGHT_ANKLE),
    "left_upper_arm": (lm.LEFT_SHOULDER, lm.LEFT_ELBOW),
    "right_upper_arm": (lm.RIGHT_SHOULDER, lm.RIGHT_ELBOW),
    "left_forearm": (lm.LEFT_ELBOW, lm.LEFT_WRIST),
    "right_forearm": (lm.RIGHT_ELBOW, lm.RIGHT_WRIST),
    "torso": (lm.LEFT_SHOULDER, lm.LEFT_HIP),
}

# Orden de prioridad de las referencias para calibrar la escala.
SCALE_REFERENCES = ["shoulder_width", "hip_width", "torso"]


def pixel_distance(landmarks, idx_a, idx_b, width, height):
    """Distancia en pixeles entre dos landmarks."""
    xa, ya = landmarks[idx_a, 0] * width, landmarks[idx_a, 1] * height
    xb, yb = landmarks[idx_b, 0] * width, landmarks[idx_b, 1] * height
    return float(np.hypot(xb - xa, yb - ya))


def estimate_scale(landmarks, width, height, reference="shoulder_width"):
    """Metros por pixel usando una distancia corporal de referencia visible."""
    if reference not in DISTANCE_PAIRS:
        return None

    idx_a, idx_b = DISTANCE_PAIRS[reference]
    if landmarks[idx_a, 3] < VISIBILITY_THRESHOLD or landmarks[idx_b, 3] < VISIBILITY_THRESHOLD:
        return None

    ref_pixels = pixel_distance(landmarks, idx_a, idx_b, width, height)
    if ref_pixels < 1e-6:
        return None

    return REFERENCE_DISTANCES[reference] / ref_pixels


def estimate_all_distances(landmarks, width, height):
    """Estima todas las distancias en metros.

    Devuelve (distancias, referencia_usada) o (None, None) si no se puede calibrar.
    """
    scale, used_reference = None, None
    for name in SCALE_REFERENCES:
        scale = estimate_scale(landmarks, width, height, name)
        if scale is not None:
            used_reference = name
            break

    if scale is None:
        return None, None

    distances = {}
    for name, (idx_a, idx_b) in DISTANCE_PAIRS.items():
        if landmarks[idx_a, 3] > VISIBILITY_THRESHOLD and landmarks[idx_b, 3] > VISIBILITY_THRESHOLD:
            distances[name] = pixel_distance(landmarks, idx_a, idx_b, width, height) * scale
    return distances, used_reference


def angle_at(point_a, point_b, point_c):
    """Ángulo en grados en point_b formado por los segmentos point_b-point_a y point_b-point_c."""
    ba = np.asarray(point_a) - np.asarray(point_b)
    bc = np.asarray(point_c) - np.asarray(point_b)
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def _visible(landmarks, *indices):
    return all(landmarks[i, 3] > VISIBILITY_THRESHOLD for i in indices)


def estimate_joint_angles(landmarks):
    """Ángulos articulares clave para análisis de sprint (dict nombre -> grados)."""
    angles = {}

    if _visible(landmarks, lm.LEFT_HIP, lm.LEFT_KNEE, lm.LEFT_ANKLE):
        angles["left_knee"] = angle_at(landmarks[lm.LEFT_HIP, :2], landmarks[lm.LEFT_KNEE, :2], landmarks[lm.LEFT_ANKLE, :2])

    if _visible(landmarks, lm.RIGHT_HIP, lm.RIGHT_KNEE, lm.RIGHT_ANKLE):
        angles["right_knee"] = angle_at(landmarks[lm.RIGHT_HIP, :2], landmarks[lm.RIGHT_KNEE, :2], landmarks[lm.RIGHT_ANKLE, :2])

    if _visible(landmarks, lm.LEFT_SHOULDER, lm.LEFT_HIP, lm.LEFT_KNEE):
        angles["left_hip"] = angle_at(landmarks[lm.LEFT_SHOULDER, :2], landmarks[lm.LEFT_HIP, :2], landmarks[lm.LEFT_KNEE, :2])

    if _visible(landmarks, lm.RIGHT_SHOULDER, lm.RIGHT_HIP, lm.RIGHT_KNEE):
        angles["right_hip"] = angle_at(landmarks[lm.RIGHT_SHOULDER, :2], landmarks[lm.RIGHT_HIP, :2], landmarks[lm.RIGHT_KNEE, :2])

    if _visible(landmarks, lm.LEFT_SHOULDER, lm.LEFT_ELBOW, lm.LEFT_WRIST):
        angles["left_elbow"] = angle_at(landmarks[lm.LEFT_SHOULDER, :2], landmarks[lm.LEFT_ELBOW, :2], landmarks[lm.LEFT_WRIST, :2])

    if _visible(landmarks, lm.RIGHT_SHOULDER, lm.RIGHT_ELBOW, lm.RIGHT_WRIST):
        angles["right_elbow"] = angle_at(landmarks[lm.RIGHT_SHOULDER, :2], landmarks[lm.RIGHT_ELBOW, :2], landmarks[lm.RIGHT_WRIST, :2])

    if _visible(landmarks, lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER, lm.LEFT_HIP, lm.RIGHT_HIP):
        mid_shoulder = (landmarks[lm.LEFT_SHOULDER, :2] + landmarks[lm.RIGHT_SHOULDER, :2]) / 2
        mid_hip = (landmarks[lm.LEFT_HIP, :2] + landmarks[lm.RIGHT_HIP, :2]) / 2
        dx = mid_shoulder[0] - mid_hip[0]
        dy = mid_shoulder[1] - mid_hip[1]
        angles["torso_inclination"] = float(np.degrees(np.arctan2(abs(dx), abs(dy))))

    return angles