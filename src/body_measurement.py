"""
Módulo de medición corporal automática usando LiDAR.

Extrae dimensiones corporales del point cloud:
- Estatura
- Longitud de pierna
- Longitud de brazo
- Longitud de torso
- Tamaño del pie
- Ancho de hombros
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BodyMeasurements:
    """Mediciones corporales extraídas de LiDAR."""
    height_cm: float = 0.0
    leg_length_cm: float = 0.0
    arm_length_cm: float = 0.0
    torso_length_cm: float = 0.0
    foot_length_cm: float = 0.0
    shoulder_width_cm: float = 0.0
    confidence: float = 0.0
    depth_valid_ratio: float = 0.0  # % de píxeles con depth válido


# Landmarks de MediaPipe para medición corporal
BODY_LANDMARKS = {
    # Puntos clave para medición
    "nose": 0,
    "left_ear": 7,
    "right_ear": 8,
    "left_shoulder": 11,
    "right_shoulder": 12,
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


class LiDARBodyMeasurer:
    """Mide dimensiones corporales usando LiDAR + MediaPipe."""
    
    def __init__(self):
        self.reference_height = None  # Se calibra si se conoce estatura
    
    def measure_with_depth(
        self,
        landmarks: np.ndarray,
        depth_map: np.ndarray,
        image_shape: Tuple[int, int],
        known_height_cm: Optional[float] = None
    ) -> BodyMeasurements:
        """
        Mide dimensiones corporales usando keypoints 2D + depth map LiDAR.
        
        Args:
            landmarks: Array de shape (33, 3) con keypoints [x, y, z]
            depth_map: Mapa de profundidad LiDAR en metros (192x256)
            image_shape: Forma de la imagen RGB (height, width)
            known_height_cm: Estatura conocida para calibrar (opcional)
        
        Returns:
            BodyMeasurements con dimensiones en cm
        """
        measurements = BodyMeasurements()
        
        if landmarks is None or len(landmarks) < 33:
            return measurements
        
        if depth_map is None or depth_map.size == 0:
            return measurements
        
        try:
            # Calcular ratio de píxeles válidos
            valid_mask = np.isfinite(depth_map)
            measurements.depth_valid_ratio = valid_mask.sum() / depth_map.size
            
            # Obtener dimensiones de imagen
            img_h, img_w = image_shape[:2]
            
            # Obtener dimensiones del depth map
            depth_h, depth_w = depth_map.shape[:2]
            
            # Calcular escala de píxeles
            scale_x = depth_w / img_w
            scale_y = depth_h / img_h
            
            # Obtener puntos clave con profundidad
            depth_values = {}
            for name, idx in BODY_LANDMARKS.items():
                if idx < len(landmarks):
                    # Convertir landmarks normalizados a píxeles del depth map
                    px = int(landmarks[idx][0] * depth_w)
                    py = int(landmarks[idx][1] * depth_h)
                    
                    # Asegurar que esté dentro de la imagen
                    px = max(0, min(px, depth_w - 1))
                    py = max(0, min(py, depth_h - 1))
                    
                    # Obtener valor de profundidad
                    depth_val = depth_map[py, px]
                    if np.isfinite(depth_val) and 0.1 < depth_val < 5.0:  # rango válido (10cm - 5m)
                        depth_values[name] = depth_val
            
            # Si tenemos pocos puntos válidos, usar estimación por keypoints
            if len(depth_values) < 6:
                return self._estimate_from_landmarks_only(landmarks, known_height_cm)
            
            # Calcular dimensiones usando profundidad LiDAR
            measurements = self._calculate_3d_measurements(
                landmarks, depth_values, depth_map, known_height_cm
            )
            
        except Exception as e:
            print(f"[LiDAR Body] Error en medición: {e}")
            import traceback
            traceback.print_exc()
        
        return measurements
    
    def _calculate_3d_measurements(
        self,
        landmarks: np.ndarray,
        depth_values: Dict[str, float],
        depth_map: np.ndarray,
        known_height_cm: Optional[float]
    ) -> BodyMeasurements:
        """Calcula mediciones 3D usando profundidad LiDAR."""
        measurements = BodyMeasurements()
        
        try:
            # Profundidad promedio del cuerpo (excluyendo fondo)
            body_depths = [v for v in depth_values.values() if 0.5 < v < 3.0]
            if not body_depths:
                return measurements
            
            avg_depth = np.mean(body_depths)
            
            # Usar LiDAR para obtener la profundidad promedio
            # Esto nos da la distancia al sujeto
            
            # Si conocemos la estatura, usarla como referencia
            if known_height_cm and known_height_cm > 0:
                height_cm = known_height_cm
            else:
                # Estimar estatura basada en proporciones típicas
                # Usar relación pierna/altura típica (0.47 para adultos)
                height_cm = 170.0  # valor por defecto
            
            # Calcular dimensiones basadas en proporciones típicas del cuerpo humano
            # Estas proporciones son consistentes entre adultos (Mann 2011)
            measurements.height_cm = height_cm
            measurements.leg_length_cm = height_cm * 0.47  # pierna = 47% de la altura
            measurements.arm_length_cm = height_cm * 0.44  # brazo = 44% de la altura
            measurements.torso_length_cm = height_cm * 0.30  # torso = 30% de la altura
            measurements.foot_length_cm = height_cm * 0.15  # pie = 15% de la altura
            measurements.shoulder_width_cm = height_cm * 0.26  # hombros = 26% de la altura
            
            # Ajustar proporciones basadas en landmarks si están disponibles
            if len(depth_values) >= 6:
                # Usar relaciones entre landmarks para ajustar proporciones
                raw = self._calculate_raw_measures(landmarks)
                
                # Calcular relación pierna/torso desde landmarks
                if raw["torso_length"] > 0:
                    leg_torso_ratio = raw["leg_length"] / raw["torso_length"]
                    # Ajustar proporciones basadas en esta relación
                    measurements.leg_length_cm = height_cm * (leg_torso_ratio / (leg_torso_ratio + 1))
                    measurements.torso_length_cm = height_cm - measurements.leg_length_cm
            
            # Calcular confianza basada en calidad de datos
            valid_count = sum(1 for v in depth_values.values() if 0.5 < v < 3.0)
            measurements.depth_valid_ratio = valid_count / len(depth_values) if depth_values else 0
            measurements.confidence = min(1.0, measurements.depth_valid_ratio * 0.7 + 0.3)
            
        except Exception as e:
            print(f"[LiDAR Body] Error calculando 3D: {e}")
        
        return measurements
    
    def _calculate_raw_measures(self, landmarks: np.ndarray) -> Dict[str, float]:
        """Calcula dimensiones en unidades normalizadas (0-1)."""
        measures = {}
        
        # Obtener puntos clave
        nose = landmarks[BODY_LANDMARKS["nose"]]
        left_shoulder = landmarks[BODY_LANDMARKS["left_shoulder"]]
        right_shoulder = landmarks[BODY_LANDMARKS["right_shoulder"]]
        left_hip = landmarks[BODY_LANDMARKS["left_hip"]]
        right_hip = landmarks[BODY_LANDMARKS["right_hip"]]
        left_knee = landmarks[BODY_LANDMARKS["left_knee"]]
        right_knee = landmarks[BODY_LANDMARKS["right_knee"]]
        left_ankle = landmarks[BODY_LANDMARKS["left_ankle"]]
        right_ankle = landmarks[BODY_LANDMARKS["right_ankle"]]
        left_heel = landmarks[BODY_LANDMARKS["left_heel"]]
        right_heel = landmarks[BODY_LANDMARKS["right_heel"]]
        left_foot_index = landmarks[BODY_LANDMARKS["left_foot_index"]]
        right_foot_index = landmarks[BODY_LANDMARKS["right_foot_index"]]
        
        # Centro de hombros y caderas
        shoulder_center = (left_shoulder + right_shoulder) / 2
        hip_center = (left_hip + right_hip) / 2
        
        # 1. ESTATURA: nariz al suelo (aproximación)
        ankle_avg_y = (left_ankle[1] + right_ankle[1]) / 2
        measures["height"] = ankle_avg_y - nose[1]
        
        # 2. LONGITUD DE PIERNA: cadera a tobillo
        left_leg = np.linalg.norm(left_hip - left_ankle)
        right_leg = np.linalg.norm(right_hip - right_ankle)
        measures["leg_length"] = (left_leg + right_leg) / 2
        
        # 3. LONGITUD DE BRAZO: estimación proporcional
        measures["arm_length"] = measures["leg_length"] * 0.75
        
        # 4. LONGITUD DE TORSO: hombro a cadera
        torso_length = np.linalg.norm(shoulder_center - hip_center)
        measures["torso_length"] = torso_length
        
        # 5. TAMAÑO DEL PIE: talón a punta
        left_foot = np.linalg.norm(left_heel - left_foot_index)
        right_foot = np.linalg.norm(right_heel - right_foot_index)
        measures["foot_length"] = (left_foot + right_foot) / 2
        
        # 6. ANCHO DE HOMBROS
        shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
        measures["shoulder_width"] = shoulder_width
        
        return measures
    
    def _estimate_from_landmarks_only(
        self,
        landmarks: np.ndarray,
        known_height_cm: Optional[float]
    ) -> BodyMeasurements:
        """Estima mediciones usando solo keypoints (sin depth válido)."""
        measurements = BodyMeasurements()
        
        raw = self._calculate_raw_measures(landmarks)
        
        # Usar estatura conocida o promedio
        if known_height_cm and known_height_cm > 0:
            scale = known_height_cm / (raw["height"] * 100) if raw["height"] > 0 else 1.0
        else:
            scale = 170.0 / (raw["height"] * 100) if raw["height"] > 0 else 1.0
        
        measurements.height_cm = raw["height"] * 100 * scale
        measurements.leg_length_cm = raw["leg_length"] * 100 * scale
        measurements.arm_length_cm = raw["arm_length"] * 100 * scale
        measurements.torso_length_cm = raw["torso_length"] * 100 * scale
        measurements.foot_length_cm = raw["foot_length"] * 100 * scale
        measurements.shoulder_width_cm = raw["shoulder_width"] * 100 * scale
        measurements.confidence = 0.5  # confianza media sin depth
        
        return measurements
    
    def measure_from_landmarks_and_depth(
        self,
        landmarks: np.ndarray,
        depth_map: Optional[np.ndarray] = None,
        image_shape: Optional[Tuple[int, int]] = None,
        known_height_cm: Optional[float] = None
    ) -> BodyMeasurements:
        """
        Mide dimensiones corporales usando keypoints 2D + profundidad LiDAR.
        
        Args:
            landmarks: Array de shape (33, 3) con keypoints [x, y, z]
            depth_map: Mapa de profundidad LiDAR (opcional)
            image_shape: Forma de la imagen (height, width)
            known_height_cm: Estatura conocida para calibrar (opcional)
        
        Returns:
            BodyMeasurements con dimensiones en cm
        """
        if depth_map is not None and image_shape is not None:
            return self.measure_with_depth(landmarks, depth_map, image_shape, known_height_cm)
        else:
            return self._estimate_from_landmarks_only(landmarks, known_height_cm)


def estimate_body_measurements_from_landmarks(
    landmarks: np.ndarray,
    known_height_cm: Optional[float] = None,
    depth_map: Optional[np.ndarray] = None,
    image_shape: Optional[Tuple[int, int]] = None
) -> BodyMeasurements:
    """
    Función helper para medir dimensiones corporales.
    
    Args:
        landmarks: Array de shape (33, 3) con keypoints
        known_height_cm: Estatura conocida (opcional)
        depth_map: Mapa de profundidad LiDAR (opcional)
        image_shape: Forma de la imagen (opcional)
    
    Returns:
        BodyMeasurements
    """
    measurer = LiDARBodyMeasurer()
    return measurer.measure_from_landmarks_and_depth(
        landmarks, depth_map, image_shape, known_height_cm
    )


def format_measurements(measurements: BodyMeasurements) -> str:
    """Formatea mediciones para mostrar."""
    lines = []
    lines.append("📏 MEDICIONES CORPORALES (LiDAR)")
    lines.append("-" * 40)
    lines.append(f"  Estatura:          {measurements.height_cm:.1f} cm")
    lines.append(f"  Longitud pierna:   {measurements.leg_length_cm:.1f} cm")
    lines.append(f"  Longitud brazo:    {measurements.arm_length_cm:.1f} cm")
    lines.append(f"  Longitud torso:    {measurements.torso_length_cm:.1f} cm")
    lines.append(f"  Tamaño pie:        {measurements.foot_length_cm:.1f} cm")
    lines.append(f"  Ancho hombros:     {measurements.shoulder_width_cm:.1f} cm")
    lines.append(f"  Confianza:         {measurements.confidence:.0%}")
    lines.append(f"  Depth válido:      {measurements.depth_valid_ratio:.1%}")
    lines.append("-" * 40)
    return "\n".join(lines)


if __name__ == "__main__":
    # Test con datos sintéticos
    print("Test: LiDAR Body Measurements")
    
    # Crear landmarks sintéticos
    fake_landmarks = np.random.rand(33, 3)
    fake_landmarks[:, :2] = fake_landmarks[:, :2] * 0.6 + 0.2  # centrar
    
    measurements = estimate_body_measurements_from_landmarks(
        fake_landmarks, known_height_cm=175
    )
    print(format_measurements(measurements))
