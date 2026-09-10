import numpy as np
from lidar.depth_utils import sample_depth_neighborhood


class SensorFusion:
    """Combina landmarks de MediaPipe con depth map para obtener coordenadas 3D reales."""

    def __init__(self, camera_intrinsics=None, depth_radius=2):
        """
        Args:
            camera_intrinsics: dict con fx, fy, cx, cy para proyeccion 3D.
            depth_radius: radio de vecindario para sampling de depth.
        """
        self.camera_intrinsics = camera_intrinsics
        self.depth_radius = depth_radius

    def fuse(self, landmarks_normalized, depth_map, rgb_width, rgb_height):
        """Fusiona landmarks normalizados con depth map.

        Args:
            landmarks_normalized: ndarray (33, 4) con [x, y, z, visibility] normalizados.
            depth_map: ndarray (H_depth, W_depth) con profundidad en metros.
            rgb_width, rgb_height: dimensiones del frame RGB.

        Returns:
            dict con:
                "positions_3d": ndarray (33, 3) con [x_m, y_m, z_m] en metros reales.
                "visibility": ndarray (33,) con visibilidad de cada landmark.
        """
        n_landmarks = landmarks_normalized.shape[0]
        positions_3d = np.zeros((n_landmarks, 3))
        visibility = landmarks_normalized[:, 3]

        for i in range(n_landmarks):
            x_norm = landmarks_normalized[i, 0]
            y_norm = landmarks_normalized[i, 1]

            # Obtener depth real del LiDAR
            z_m = sample_depth_neighborhood(
                depth_map, x_norm, y_norm, rgb_width, rgb_height, self.depth_radius
            )

            if np.isnan(z_m):
                positions_3d[i] = [np.nan, np.nan, np.nan]
                continue

            # Convertir a coordenadas 3D reales usando proyeccion pinhole
            if self.camera_intrinsics is not None:
                fx = self.camera_intrinsics["fx"]
                fy = self.camera_intrinsics["fy"]
                cx = self.camera_intrinsics["cx"]
                cy = self.camera_intrinsics["cy"]

                x_m = (x_norm * rgb_width - cx) * z_m / fx
                y_m = (y_norm * rgb_height - cy) * z_m / fy
            else:
                # Sin intrinsecos, usar coordenadas normalizadas * depth
                x_m = (x_norm - 0.5) * z_m
                y_m = (y_norm - 0.5) * z_m

            positions_3d[i] = [x_m, y_m, z_m]

        return {
            "positions_3d": positions_3d,
            "visibility": visibility,
        }

    def get_distance_between_points(self, positions_3d, idx_a, idx_b):
        """Calcula distancia euclidiana entre dos landmarks en metros.

        Args:
            positions_3d: ndarray (33, 3) con coordenadas 3D.
            idx_a, idx_b: indices de los landmarks.

        Returns:
            float: distancia en metros, o NaN si algun punto es invalido.
        """
        a = positions_3d[idx_a]
        b = positions_3d[idx_b]

        if np.any(np.isnan(a)) or np.any(np.isnan(b)):
            return np.nan

        return float(np.linalg.norm(a - b))

    def get_height_from_ground(self, positions_3d, ankle_idx, hip_idx):
        """Calcula altura de un punto respecto al suelo (usando tobillo como referencia).

        Args:
            positions_3d: ndarray (33, 3).
            ankle_idx: indice del tobillo de referencia.
            hip_idx: indice del punto a medir (ej: cadera).

        Returns:
            float: altura en metros, o NaN.
        """
        ankle = positions_3d[ankle_idx]
        point = positions_3d[hip_idx]

        if np.any(np.isnan(ankle)) or np.any(np.isnan(point)):
            return np.nan

        # Altura relativa al suelo (eje Y en MediaPipe va de arriba a abajo)
        # En coordenadas 3D reales, Y negativo = arriba
        return float(abs(ankle[1] - point[1]))
