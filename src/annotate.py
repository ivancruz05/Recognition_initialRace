"""Dibujo de keypoints y overlays de información sobre frames."""

import cv2

from src import landmarks as lm
from src.config import VISIBILITY_THRESHOLD

SKELETON_COLOR = (0, 255, 0)
OUTLINE_COLOR = (255, 255, 255)
DEFAULT_POINT_COLOR = (0, 255, 0)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_keypoints(frame, landmarks, colored_groups=True):
    """Dibuja un círculo por cada keypoint visible, opcionalmente coloreado por grupo."""
    height, width = frame.shape[:2]

    for idx in range(lm.NUM_LANDMARKS):
        if landmarks[idx, 3] < VISIBILITY_THRESHOLD:
            continue

        x, y = int(landmarks[idx, 0] * width), int(landmarks[idx, 1] * height)
        color = _group_color(idx) if colored_groups else DEFAULT_POINT_COLOR
        cv2.circle(frame, (x, y), 6, color, -1)
        cv2.circle(frame, (x, y), 8, OUTLINE_COLOR, 1)


def draw_skeleton(frame, landmarks):
    """Dibuja las conexiones del esqueleto entre keypoints visibles."""
    height, width = frame.shape[:2]

    for idx_a, idx_b in lm.CONNECTIONS:
        if landmarks[idx_a, 3] < VISIBILITY_THRESHOLD or landmarks[idx_b, 3] < VISIBILITY_THRESHOLD:
            continue

        pt_a = (int(landmarks[idx_a, 0] * width), int(landmarks[idx_a, 1] * height))
        pt_b = (int(landmarks[idx_b, 0] * width), int(landmarks[idx_b, 1] * height))
        cv2.line(frame, pt_a, pt_b, SKELETON_COLOR, 2)


def draw_lines(frame, lines, x=10, y=25, step=20, scale=0.5, thickness=1):
    """Dibuja líneas de texto. lines es una secuencia de (texto, color BGR)."""
    cursor = y
    for text, color in lines:
        cv2.putText(frame, text, (x, cursor), FONT, scale, color, thickness)
        cursor += step
    return cursor


def _group_color(idx):
    for group, indices in lm.GROUP_INDICES.items():
        if idx in indices:
            return lm.GROUP_COLORS[group]
    return DEFAULT_POINT_COLOR