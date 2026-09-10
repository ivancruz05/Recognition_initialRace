"""Fusión de landmarks (MediaPipe) con depth map para coordenadas 3D reales."""

import numpy as np

from src.depth import sample_depth_neighborhood


class SensorFusion:
    """Combina landmarks normalizados con profundidad para obtener metros reales."""

    def __init__(self, camera_intrinsics=None, depth_radius=2):
        self.camera_intrinsics = camera_intrinsics
        self.depth_radius = depth_radius

    def fuse(self, landmarks_normalized, depth_map, rgb_width, rgb_height):
        """Devuelve dict con "positions_3d" (33, 3) en metros y "visibility" (33,).

        Las posiciones inválidas quedan con NaN.
        """
        n = landmarks_normalized.shape[0]
        positions_3d = np.zeros((n, 3))
        visibility = landmarks_normalized[:, 3]

        for i in range(n):
            x_norm, y_norm = landmarks_normalized[i, 0], landmarks_normalized[i, 1]

            z_m = sample_depth_neighborhood(
                depth_map, x_norm, y_norm, rgb_width, rgb_height, self.depth_radius
            )

            if np.isnan(z_m):
                positions_3d[i] = np.nan
                continue

            if self.camera_intrinsics is not None:
                fx = self.camera_intrinsics["fx"]
                fy = self.camera_intrinsics["fy"]
                cx = self.camera_intrinsics["cx"]
                cy = self.camera_intrinsics["cy"]
                x_m = (x_norm * rgb_width - cx) * z_m / fx
                y_m = (y_norm * rgb_height - cy) * z_m / fy
            else:
                x_m = (x_norm - 0.5) * z_m
                y_m = (y_norm - 0.5) * z_m

            positions_3d[i] = [x_m, y_m, z_m]

        return {"positions_3d": positions_3d, "visibility": visibility}

    def get_distance_between_points(self, positions_3d, idx_a, idx_b):
        """Distancia euclidiana en metros entre dos landmarks, o NaN si inválidos."""
        point_a = positions_3d[idx_a]
        point_b = positions_3d[idx_b]

        if np.any(np.isnan(point_a)) or np.any(np.isnan(point_b)):
            return np.nan
        return float(np.linalg.norm(point_a - point_b))

    def get_height_from_ground(self, positions_3d, ankle_idx, hip_idx):
        """Altura en metros de un punto respecto al nivel del tobillo, o NaN."""
        ankle = positions_3d[ankle_idx]
        point = positions_3d[hip_idx]

        if np.any(np.isnan(ankle)) or np.any(np.isnan(point)):
            return np.nan
        return float(abs(ankle[1] - point[1]))