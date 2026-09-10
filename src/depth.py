"""Utilidades para mapas de profundidad (LiDAR) y nubes de puntos."""

import numpy as np

from src.config import MAX_DEPTH_METERS


def sample_depth_at_landmark(depth_map, x_norm, y_norm, width, height):
    """Profundidad en metros en la posición de un landmark, o NaN si inválida."""
    h_depth, w_depth = depth_map.shape

    x_depth = min(max(int(x_norm * (w_depth - 1)), 0), w_depth - 1)
    y_depth = min(max(int(y_norm * (h_depth - 1)), 0), h_depth - 1)

    value = depth_map[y_depth, x_depth]
    if np.isnan(value) or value <= 0 or value > MAX_DEPTH_METERS:
        return np.nan
    return float(value)


def sample_depth_neighborhood(depth_map, x_norm, y_norm, width, height, radius=2):
    """Profundidad promedio (mediana) en un vecindario del landmark.

    Más robusto que el muestreo individual ante ruido del sensor.
    """
    h_depth, w_depth = depth_map.shape

    x_depth = int(x_norm * (w_depth - 1))
    y_depth = int(y_norm * (h_depth - 1))

    x_min = max(0, x_depth - radius)
    x_max = min(w_depth, x_depth + radius + 1)
    y_min = max(0, y_depth - radius)
    y_max = min(h_depth, y_depth + radius + 1)

    neighborhood = depth_map[y_min:y_max, x_min:x_max]
    valid = neighborhood[(neighborhood > 0) & (neighborhood < MAX_DEPTH_METERS) & ~np.isnan(neighborhood)]

    if len(valid) == 0:
        return np.nan
    return float(np.median(valid))


def depth_map_to_point_cloud(depth_map, rgb_frame, camera_intrinsics=None, max_depth=5.0):
    """Convierte depth map + RGB en (puntos 3D en metros, colores RGB normalizados)."""
    h, w = depth_map.shape

    if camera_intrinsics is None:
        camera_intrinsics = {
            "fx": w * 0.8,
            "fy": h * 0.8,
            "cx": w / 2.0,
            "cy": h / 2.0,
        }

    fx = camera_intrinsics["fx"]
    fy = camera_intrinsics["fy"]
    cx = camera_intrinsics["cx"]
    cy = camera_intrinsics["cy"]

    u, v = np.meshgrid(np.arange(w), np.arange(h))
    valid = (depth_map > 0) & (depth_map < max_depth) & ~np.isnan(depth_map)

    z = depth_map[valid]
    x = (u[valid] - cx) * z / fx
    y = (v[valid] - cy) * z / fy
    points = np.stack([x, y, z], axis=-1)

    if rgb_frame.shape[:2] == depth_map.shape:
        colors = rgb_frame[valid][:, ::-1] / 255.0  # BGR -> RGB normalizado
    else:
        colors = np.full((len(points), 3), 0.5)

    return points, colors


def normalize_depth_map(depth_map, target_min=0.0, target_max=5.0):
    """Normaliza un depth map a un rango objetivo."""
    valid = depth_map[(depth_map > 0) & ~np.isnan(depth_map)]

    if len(valid) == 0:
        return depth_map

    src_min = np.percentile(valid, 2)
    src_max = np.percentile(valid, 98)

    if src_max - src_min < 1e-6:
        return np.full_like(depth_map, (target_min + target_max) / 2)

    normalized = np.clip((depth_map - src_min) / (src_max - src_min), 0, 1)
    return normalized * (target_max - target_min) + target_min