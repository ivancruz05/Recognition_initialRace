import numpy as np
from pathlib import Path


def sample_depth_at_landmark(depth_map, x_norm, y_norm, width, height):
    """Muestra el valor de depth en la posicion de un landmark normalizado.

    Args:
        depth_map: ndarray (H_depth, W_depth) con valores de profundidad en metros.
        x_norm, y_norm: coordenadas normalizadas del landmark (0-1).
        width, height: dimensiones del frame RGB.

    Returns:
        float: profundidad en metros, o NaN si fuera de rango.
    """
    h_depth, w_depth = depth_map.shape

    # Convertir coordenadas normalizadas a pixeles del depth map
    x_depth = int(x_norm * (w_depth - 1))
    y_depth = int(y_norm * (h_depth - 1))

    x_depth = max(0, min(x_depth, w_depth - 1))
    y_depth = max(0, min(y_depth, h_depth - 1))

    depth_value = depth_map[y_depth, x_depth]

    # Filtrar valores invalidos
    if np.isnan(depth_value) or depth_value <= 0 or depth_value > 10.0:
        return np.nan

    return float(depth_value)


def sample_depth_neighborhood(depth_map, x_norm, y_norm, width, height, radius=2):
    """Muestra depth promedio en un vecindario del landmark.

    Mas robusto que sample individual ante ruido del LiDAR.

    Args:
        depth_map: ndarray (H_depth, W_depth) con valores de profundidad en metros.
        x_norm, y_norm: coordenadas normalizadas del landmark (0-1).
        width, height: dimensiones del frame RGB.
        radius: radio de vecindario en pixeles del depth map.

    Returns:
        float: profundidad promedio en metros, o NaN si no hay datos validos.
    """
    h_depth, w_depth = depth_map.shape

    x_depth = int(x_norm * (w_depth - 1))
    y_depth = int(y_norm * (h_depth - 1))

    x_min = max(0, x_depth - radius)
    x_max = min(w_depth, x_depth + radius + 1)
    y_min = max(0, y_depth - radius)
    y_max = min(h_depth, y_depth + radius + 1)

    neighborhood = depth_map[y_min:y_max, x_min:x_max]

    # Filtrar valores validos
    valid = neighborhood[(neighborhood > 0) & (neighborhood < 10.0) & ~np.isnan(neighborhood)]

    if len(valid) == 0:
        return np.nan

    return float(np.median(valid))


def depth_map_to_point_cloud(depth_map, rgb_frame, camera_intrinsics=None, max_depth=5.0):
    """Convierte un depth map + RGB en point cloud 3D.

    Args:
        depth_map: ndarray (H, W) con profundidad en metros.
        rgb_frame: ndarray (H, W, 3) en BGR.
        camera_intrinsics: dict con fx, fy, cx, cy. Si None, usa valores por defecto.
        max_depth: profundidad maxima a considerar.

    Returns:
        points: ndarray (N, 3) coordenadas 3D en metros.
        colors: ndarray (N, 3) colores RGB normalizados.
    """
    h, w = depth_map.shape

    if camera_intrinsics is None:
        # Valores por defecto para iPhone LiDAR (aproximados)
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

    # Crear grid de coordenadas de pixel
    u, v = np.meshgrid(np.arange(w), np.arange(h))

    # Filtrar depth valida
    valid = (depth_map > 0) & (depth_map < max_depth) & ~np.isnan(depth_map)

    z = depth_map[valid]
    x = (u[valid] - cx) * z / fx
    y = (v[valid] - cy) * z / fy

    points = np.stack([x, y, z], axis=-1)

    # Colores
    if rgb_frame.shape[:2] == depth_map.shape:
        colors_bgr = rgb_frame[valid]
        colors = colors_bgr[:, ::-1] / 255.0  # BGR -> RGB, normalizar
    else:
        colors = np.ones((len(points), 3)) * 0.5

    return points, colors


def normalize_depth_map(depth_map, target_min=0.0, target_max=5.0):
    """Normaliza un depth map a un rango especifico.

    Args:
        depth_map: ndarray con valores de profundidad.
        target_min, target_max: rango objetivo.

    Returns:
        ndarray normalizado.
    """
    valid = depth_map[(depth_map > 0) & ~np.isnan(depth_map)]

    if len(valid) == 0:
        return depth_map

    src_min = np.percentile(valid, 2)
    src_max = np.percentile(valid, 98)

    if src_max - src_min < 1e-6:
        return np.full_like(depth_map, (target_min + target_max) / 2)

    normalized = (depth_map - src_min) / (src_max - src_min)
    normalized = np.clip(normalized, 0, 1)

    return normalized * (target_max - target_min) + target_min
