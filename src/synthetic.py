"""Generación de datos sintéticos para validar el pipeline (FASE 1).

Simula un atleta en posición de arranque con vista lateral.
"""

import cv2
import numpy as np

from src import landmarks as lm
from src.config import (
    DEFAULT_DEPTH_HEIGHT,
    DEFAULT_DEPTH_WIDTH,
    DEFAULT_FRAME_HEIGHT,
    DEFAULT_FRAME_WIDTH,
)

# Posiciones normalizadas (0-1) de un atleta en bloques de salida.
STARTING_POSITION_LANDMARKS = {
    "nose": (0.35, 0.22),
    "left_shoulder": (0.33, 0.32),
    "right_shoulder": (0.37, 0.33),
    "left_elbow": (0.28, 0.40),
    "right_elbow": (0.32, 0.42),
    "left_wrist": (0.24, 0.48),
    "right_wrist": (0.28, 0.50),
    "left_hip": (0.38, 0.50),
    "right_hip": (0.42, 0.51),
    "left_knee": (0.48, 0.62),
    "right_knee": (0.54, 0.65),
    "left_ankle": (0.42, 0.78),
    "right_ankle": (0.58, 0.80),
    "left_heel": (0.40, 0.80),
    "right_heel": (0.56, 0.82),
    "left_foot_index": (0.36, 0.82),
    "right_foot_index": (0.62, 0.82),
}

_SKELETON_CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"),
    ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"),
    ("right_ankle", "right_heel"),
    ("left_heel", "left_foot_index"),
    ("right_heel", "right_foot_index"),
]

_JOINT_DEPTHS = {
    "left_shoulder": -0.10,
    "right_shoulder": -0.08,
    "left_elbow": -0.05,
    "right_elbow": -0.03,
    "left_wrist": 0.02,
    "right_wrist": 0.05,
    "left_hip": 0.05,
    "right_hip": 0.08,
    "left_knee": 0.15,
    "right_knee": 0.18,
    "left_ankle": 0.10,
    "right_ankle": 0.12,
    "left_foot_index": 0.08,
    "right_foot_index": 0.10,
}


def generate_skeleton_image(width=DEFAULT_FRAME_WIDTH, height=DEFAULT_FRAME_HEIGHT,
                            scale=1.0, offset_x=0.0, offset_y=0.0):
    """Imagen BGR con el skeleton del atleta en posición de arranque."""
    img = np.full((height, width, 3), 240, dtype=np.uint8)

    start_line_x = int(0.2 * width)
    cv2.line(img, (start_line_x, 0), (start_line_x, height), (0, 0, 200), 2)

    def to_px(name):
        x, y = STARTING_POSITION_LANDMARKS[name]
        return int((x + offset_x) * scale * width), int((y + offset_y) * scale * height)

    for idx_a, idx_b in _SKELETON_CONNECTIONS:
        cv2.line(img, to_px(idx_a), to_px(idx_b), (80, 80, 80), 2)

    for name, (x, y) in STARTING_POSITION_LANDMARKS.items():
        color = (0, 120, 255) if "left" in name else (255, 120, 0)
        cv2.circle(img, to_px(name), 5, color, -1)

    cv2.putText(img, "Synthetic Sprint Start", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    return img


def generate_depth_map(width=DEFAULT_DEPTH_WIDTH, height=DEFAULT_DEPTH_HEIGHT,
                       base_depth=2.0, noise_level=0.02):
    """Depth map sintético (metros) simulando un atleta a ~2 metros."""
    depth = np.full((height, width), base_depth, dtype=np.float32)

    _draw_depth_blob(depth, 0.35, 0.22, 0.06, base_depth - 0.15, width, height)
    for name, delta in _JOINT_DEPTHS.items():
        x, y = STARTING_POSITION_LANDMARKS[name]
        _draw_depth_blob(depth, x, y, 0.05, base_depth + delta, width, height)

    depth += np.random.normal(0, noise_level, depth.shape).astype(np.float32)

    background = depth == base_depth
    depth[background] = base_depth + np.random.normal(
        0, noise_level * 0.3, background.sum()
    ).astype(np.float32)

    return depth


def _draw_depth_blob(depth, cx_norm, cy_norm, radius_norm, value, img_w, img_h):
    """Dibuja un blob circular de profundidad en el depth map."""
    h, w = depth.shape
    cx, cy = int(cx_norm * w), int(cy_norm * h)
    r = max(int(radius_norm * w), int(radius_norm * h))

    y_min, y_max = max(0, cy - r), min(h, cy + r + 1)
    x_min, x_max = max(0, cx - r), min(w, cx + r + 1)

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < r:
                factor = 1.0 - (dist / r) ** 2
                depth[y, x] = depth[y, x] * (1 - factor) + value * factor


def generate_synthetic_frame(width=DEFAULT_FRAME_WIDTH, height=DEFAULT_FRAME_HEIGHT,
                             depth_width=DEFAULT_DEPTH_WIDTH, depth_height=DEFAULT_DEPTH_HEIGHT):
    """Devuelve (frame_rgb_bgr, depth_map) sintéticos."""
    return generate_skeleton_image(width, height), generate_depth_map(depth_width, depth_height)


def synthetic_landmarks_array():
    """Landmarks (33, 4) completos a partir de la posición sintética de arranque."""
    landmarks = np.zeros((33, 4))

    for name, idx in lm.LANDMARKS.items():
        if name in STARTING_POSITION_LANDMARKS:
            x, y = STARTING_POSITION_LANDMARKS[name]
            landmarks[idx] = [x, y, 0.0, 1.0]

    _interpolate_missing(landmarks)
    return landmarks


def _interpolate_missing(landmarks):
    """Completa landmarks derivados (cuello y media cadera) desde los conocidos."""
    if np.any(landmarks[lm.LEFT_SHOULDER]) and np.any(landmarks[lm.RIGHT_SHOULDER]):
        landmarks[1] = (landmarks[lm.LEFT_SHOULDER] + landmarks[lm.RIGHT_SHOULDER]) / 2
        landmarks[1][3] = 1.0

    if np.any(landmarks[lm.LEFT_HIP]) and np.any(landmarks[lm.RIGHT_HIP]):
        landmarks[22] = (landmarks[lm.LEFT_HIP] + landmarks[lm.RIGHT_HIP]) / 2
        landmarks[22][3] = 1.0


def generate_synthetic_video(output_path, n_frames=30, fps=30,
                             width=DEFAULT_FRAME_WIDTH, height=DEFAULT_FRAME_HEIGHT):
    """Genera un video con ligera variación frame a frame de la posición."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for _ in range(n_frames):
        offset_x = np.random.uniform(-0.01, 0.01)
        offset_y = np.random.uniform(-0.01, 0.01)
        frame = generate_skeleton_image(width, height, offset_x=offset_x, offset_y=offset_y)
        writer.write(frame)

    writer.release()
    return output_path


def save_depth_map(depth_map, output_path):
    """Guarda un depth map como archivo numpy."""
    np.save(str(output_path), depth_map)
    return output_path