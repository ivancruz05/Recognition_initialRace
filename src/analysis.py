"""
Análisis biomecánico de posición de salida de sprint.
Calcula ángulos articulares, distancias y métricas de posición.

Landmarks de MediaPipe (33 puntos):
  0: nose, 11: left_shoulder, 12: right_shoulder
  13: left_elbow, 14: right_elbow, 15: left_wrist, 16: right_wrist
  23: left_hip, 24: right_hip
  25: left_knee, 26: right_knee
  27: left_ankle, 28: right_ankle
  29: left_heel, 30: right_heel
  31: left_foot_index, 32: right_foot_index
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class JointAngles:
    """Ángulos articulares calculados."""
    left_knee: float      # ángulo de rodilla izquierda (grados)
    right_knee: float     # ángulo de rodilla derecha (grados)
    left_hip: float       # ángulo de cadera izquierda
    right_hip: float      # ángulo de cadera derecha
    left_ankle: float     # ángulo de tobillo izquierdo
    right_ankle: float    # ángulo de tobillo derecho
    trunk_angle: float    # ángulo del tronco (inclinación)


@dataclass
class PositionMetrics:
    """Métricas de posición."""
    hip_height: float           # altura de cadera al suelo
    distance_between_feet: float # distancia entre pies
    center_of_mass_x: float    # centro de masa horizontal
    center_of_mass_y: float    # centro de masa vertical
    support_base: float        # base de soporte


def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Calcula el ángulo entre tres puntos (en grados).
    El ángulo está en el punto b.
    
    Args:
        a, b, c: puntos 3D (x, y, z) o 2D (x, y)
    
    Returns:
        ángulo en grados (0-180)
    """
    ba = a - b
    bc = c - b
    
    # Producto punto
    dot_product = np.dot(ba, bc)
    
    # Magnitudes
    mag_ba = np.linalg.norm(ba)
    mag_bc = np.linalg.norm(bc)
    
    if mag_ba == 0 or mag_bc == 0:
        return 0.0
    
    # Coseno del ángulo
    cos_angle = dot_product / (mag_ba * mag_bc)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    
    # Ángulo en grados
    angle = np.degrees(np.arccos(cos_angle))
    return float(angle)


def calculate_knee_angle(hip: np.ndarray, knee: np.ndarray, ankle: np.ndarray) -> float:
    """
    Calcula el ángulo de flexión de la rodilla.
    
    En posición de salida:
    - Rodilla flexionada ~90-120°
    - 180° =完全 extendida
    """
    return calculate_angle(hip, knee, ankle)


def calculate_hip_angle(shoulder: np.ndarray, hip: np.ndarray, knee: np.ndarray) -> float:
    """
    Calcula el ángulo de la cadera (flexión/extensión).
    
    En posición de salida:
    - Cadera flexionada ~45-90°
    - 90° = perpendicular al torso
    """
    return calculate_angle(shoulder, hip, knee)


def calculate_ankle_angle(knee: np.ndarray, ankle: np.ndarray, foot: np.ndarray) -> float:
    """
    Calcula el ángulo del tobillo (dorsiflexión/plantarflexión).
    
    En posición de salida:
    - Dorsiflexión ~20-30° (pie levantado)
    - Plantarflexión ~0° (pie plano)
    """
    return calculate_angle(knee, ankle, foot)


def calculate_trunk_angle(nose: np.ndarray, shoulder: np.ndarray, hip: np.ndarray) -> float:
    """
    Calcula el ángulo de inclinación del tronco.
    
    En posición de salida:
    - Inclinación hacia adelante ~30-45°
    - 0° = vertical
    """
    # Vector del tronco (cadera a hombro)
    trunk_vector = shoulder - hip
    
    # Vector vertical (hacia arriba, eje Y negativo en MediaPipe)
    vertical = np.array([0, -1, 0])
    
    # Ángulo con la vertical
    cos_angle = np.dot(trunk_vector, vertical) / (np.linalg.norm(trunk_vector) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    
    angle = np.degrees(np.arccos(cos_angle))
    return float(angle)


def analyze_sprint_start(landmarks: np.ndarray) -> Dict:
    """
    Analiza la posición de salida de sprint.
    
    Args:
        landmarks: ndarray (33, 4) con [x, y, z, visibility] normalizados
    
    Returns:
        dict con métricas de análisis
    """
    # Extraer puntos clave
    nose = landmarks[0, :3]
    left_shoulder = landmarks[11, :3]
    right_shoulder = landmarks[12, :3]
    left_hip = landmarks[23, :3]
    right_hip = landmarks[24, :3]
    left_knee = landmarks[25, :3]
    right_knee = landmarks[26, :3]
    left_ankle = landmarks[27, :3]
    right_ankle = landmarks[28, :3]
    left_heel = landmarks[29, :3]
    right_heel = landmarks[30, :3]
    left_foot = landmarks[31, :3]
    right_foot = landmarks[32, :3]
    
    # Puntos medios
    mid_shoulder = (left_shoulder + right_shoulder) / 2
    mid_hip = (left_hip + right_hip) / 2
    
    # Calcular ángulos
    left_knee_angle = calculate_knee_angle(left_hip, left_knee, left_ankle)
    right_knee_angle = calculate_knee_angle(right_hip, right_knee, right_ankle)
    
    left_hip_angle = calculate_hip_angle(left_shoulder, left_hip, left_knee)
    right_hip_angle = calculate_hip_angle(right_shoulder, right_hip, right_knee)
    
    left_ankle_angle = calculate_ankle_angle(left_knee, left_ankle, left_foot)
    right_ankle_angle = calculate_ankle_angle(right_knee, right_ankle, right_foot)
    
    trunk_angle = calculate_trunk_angle(nose, mid_shoulder, mid_hip)
    
    # Métricas de posición
    # Altura de cadera (distancia vertical al suelo)
    # En MediaPipe, Y va de arriba (0) a abajo (1)
    # El suelo está en el tobillo más bajo
    ground_y = max(left_ankle[1], right_ankle[1])
    hip_height = ground_y - mid_hip[1]  # positivo = más alto
    
    # Distancia entre pies
    distance_between_feet = np.linalg.norm(left_foot - right_foot)
    
    # Centro de masa (aproximado)
    # Usar puntos medios de cada segmento con pesos aproximados
    segment_masses = {
        'head': (nose, 0.08),
        'torso': (mid_shoulder, 0.35),
        'hip': (mid_hip, 0.15),
        'left_thigh': ((left_hip + left_knee) / 2, 0.10),
        'right_thigh': ((right_hip + right_knee) / 2, 0.10),
        'left_calf': ((left_knee + left_ankle) / 2, 0.05),
        'right_calf': ((right_knee + right_ankle) / 2, 0.05),
        'left_foot': (left_foot, 0.01),
        'right_foot': (right_foot, 0.01),
    }
    
    com_x = sum(pos[0] * mass for pos, mass in segment_masses.values())
    com_y = sum(pos[1] * mass for pos, mass in segment_masses.values())
    
    # Base de soporte (distancia horizontal entre pies)
    support_base = abs(left_foot[0] - right_foot[0])
    
    # Verificar visibilidad
    visibility = {
        'left_knee': landmarks[25, 3] > 0.5,
        'right_knee': landmarks[26, 3] > 0.5,
        'left_ankle': landmarks[27, 3] > 0.5,
        'right_ankle': landmarks[28, 3] > 0.5,
        'left_hip': landmarks[23, 3] > 0.5,
        'right_hip': landmarks[24, 3] > 0.5,
    }
    
    # Calidad de la posición
    quality_score = _calculate_quality_score(
        left_knee_angle, right_knee_angle,
        left_hip_angle, right_hip_angle,
        trunk_angle
    )
    
    return {
        'angles': {
            'left_knee': left_knee_angle,
            'right_knee': right_knee_angle,
            'left_hip': left_hip_angle,
            'right_hip': right_hip_angle,
            'left_ankle': left_ankle_angle,
            'right_ankle': right_ankle_angle,
            'trunk': trunk_angle,
        },
        'position': {
            'hip_height': hip_height,
            'distance_between_feet': distance_between_feet,
            'center_of_mass_x': com_x,
            'center_of_mass_y': com_y,
            'support_base': support_base,
        },
        'visibility': visibility,
        'quality_score': quality_score,
        'recommendations': _generate_recommendations(
            left_knee_angle, right_knee_angle,
            left_hip_angle, right_hip_angle,
            trunk_angle, hip_height
        ),
    }


def _calculate_quality_score(
    left_knee: float, right_knee: float,
    left_hip: float, right_hip: float,
    trunk: float
) -> float:
    """
    Calcula un puntaje de calidad de posición (0-100).
    
    Basado en rangos óptimos para posición de salida de sprint:
    - Rodilla: 90-120° (flexionada)
    - Cadera: 45-90° (flexionada)
    - Tronco: 15-45° (inclinado hacia adelante)
    """
    scores = []
    
    # Rodilla: óptimo 90-120°
    for knee in [left_knee, right_knee]:
        if 90 <= knee <= 120:
            scores.append(100)
        elif 70 <= knee < 90 or 120 < knee <= 140:
            scores.append(70)
        elif 50 <= knee < 70 or 140 < knee <= 160:
            scores.append(40)
        else:
            scores.append(20)
    
    # Cadera: óptimo 45-90°
    for hip in [left_hip, right_hip]:
        if 45 <= hip <= 90:
            scores.append(100)
        elif 30 <= hip < 45 or 90 < hip <= 110:
            scores.append(70)
        elif 15 <= hip < 30 or 110 < hip <= 130:
            scores.append(40)
        else:
            scores.append(20)
    
    # Tronco: óptimo 15-45°
    if 15 <= trunk <= 45:
        scores.append(100)
    elif 5 <= trunk < 15 or 45 < trunk <= 60:
        scores.append(70)
    elif trunk < 5 or 60 < trunk <= 75:
        scores.append(40)
    else:
        scores.append(20)
    
    return float(np.mean(scores))


def _generate_recommendations(
    left_knee: float, right_knee: float,
    left_hip: float, right_hip: float,
    trunk: float, hip_height: float
) -> List[str]:
    """Genera recomendaciones basadas en los ángulos."""
    recommendations = []
    
    # Rodilla
    avg_knee = (left_knee + right_knee) / 2
    if avg_knee < 80:
        recommendations.append("Rodillas muy flexionadas. Extiende ligeramente para más potencia.")
    elif avg_knee > 130:
        recommendations.append("Rodillas poco flexionadas. Flexiona más para mejor impulso.")
    
    # Cadera
    avg_hip = (left_hip + right_hip) / 2
    if avg_hip < 40:
        recommendations.append("Cadera muy cerrada. Abre más el ángulo de cadera.")
    elif avg_hip > 100:
        recommendations.append("Cadera muy abierta. Cierra más el ángulo.")
    
    # Tronco
    if trunk < 10:
        recommendations.append("Tronco muy vertical. Inclínate más hacia adelante.")
    elif trunk > 50:
        recommendations.append("Tronco muy inclinado. Endereza ligeramente.")
    
    # Altura de cadera
    if hip_height < 0.3:
        recommendations.append("Cadera muy baja. Levántate un poco más.")
    elif hip_height > 0.6:
        recommendations.append("Cadera muy alta. Baja un poco más.")
    
    if not recommendations:
        recommendations.append("Posición dentro de los rangos óptimos.")
    
    return recommendations


def format_analysis_report(analysis: Dict, frame_idx: int = None) -> str:
    """Formatea un reporte legible del análisis."""
    lines = []
    
    if frame_idx is not None:
        lines.append(f"=== ANÁLISIS DE FRAME {frame_idx} ===\n")
    else:
        lines.append("=== ANÁLISIS DE POSICIÓN DE SALIDA ===\n")
    
    # Ángulos
    lines.append("📐 ÁNGULOS ARTICULARES:")
    angles = analysis['angles']
    lines.append(f"  Rodilla izquierda:    {angles['left_knee']:.1f}°")
    lines.append(f"  Rodilla derecha:      {angles['right_knee']:.1f}°")
    lines.append(f"  Cadera izquierda:     {angles['left_hip']:.1f}°")
    lines.append(f"  Cadera derecha:       {angles['right_hip']:.1f}°")
    lines.append(f"  Tobillo izquierdo:    {angles['left_ankle']:.1f}°")
    lines.append(f"  Tobillo derecho:      {angles['right_ankle']:.1f}°")
    lines.append(f"  Tronco:               {angles['trunk']:.1f}°")
    
    # Posición
    lines.append("\n📏 MÉTRICAS DE POSICIÓN:")
    pos = analysis['position']
    lines.append(f"  Altura de cadera:     {pos['hip_height']:.3f}")
    lines.append(f"  Distancia entre pies: {pos['distance_between_feet']:.3f}")
    lines.append(f"  Base de soporte:      {pos['support_base']:.3f}")
    
    # Calidad
    lines.append(f"\n⭐ CALIDAD: {analysis['quality_score']:.0f}/100")
    
    # Recomendaciones
    lines.append("\n💡 RECOMENDACIONES:")
    for rec in analysis['recommendations']:
        lines.append(f"  • {rec}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test con un frame
    import cv2
    from src.pose import PoseDetector
    
    frame_path = "data/r3d_extracted/frame_000100.png"
    rgb = cv2.imread(frame_path)
    
    with PoseDetector(model_complexity=2) as detector:
        results = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
        
        if results:
            landmarks = detector.get_landmarks_normalized(results)
            analysis = analyze_sprint_start(landmarks)
            print(format_analysis_report(analysis, frame_idx=100))
