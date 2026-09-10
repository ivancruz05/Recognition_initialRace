"""
Módulo de Machine Learning para predicciones de sprint.
Analiza keypoints 2D de video para predecir:
- Calidad de posición (1-10)
- Tiempo estimado de reacción
- Errores comunes
- Recomendaciones personalizadas
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class SprintFeatures:
    """Features extraídas de keypoints para ML."""
    # Ángulos
    knee_angle_front: float
    knee_angle_rear: float
    hip_angle_front: float
    hip_angle_rear: float
    ankle_angle_front: float
    ankle_angle_rear: float
    trunk_angle: float
    
    # Diferencias
    knee_diff: float
    hip_diff: float
    symmetry_score: float
    
    # Posición
    height_ratio: float
    foot_distance: float
    support_base: float
    center_of_mass_x: float
    
    # Datos corporales (LiDAR)
    height_cm: float = 0.0
    weight_kg: float = 0.0
    leg_length_cm: float = 0.0
    arm_length_cm: float = 0.0
    torso_length_cm: float = 0.0
    foot_length_cm: float = 0.0
    shoulder_width_cm: float = 0.0
    age: int = 0
    sex: str = "M"
    
    # Estabilidad (si hay múltiples frames)
    angle_variance: float = 0.0
    movement_smoothness: float = 0.0


@dataclass
class Prediction:
    """Predicción del modelo ML."""
    quality_score: float        # 1-10
    reaction_time: float        # segundos estimados
    confidence: float           # 0-1
    errors_detected: List[str]
    recommendations: List[str]
    features_used: Dict[str, float]


def extract_features_from_analysis(
    analysis: Dict,
    body_measurements: Optional[Dict] = None,
    athlete_data: Optional[Dict] = None
) -> SprintFeatures:
    """
    Extrae features ML del análisis biomecánico + datos corporales.
    
    Args:
        analysis: resultado de analyze_sprint_start()
        body_measurements: mediciones LiDAR (height_cm, leg_length_cm, etc.)
        athlete_data: datos manuales (weight_kg, age, sex)
    
    Returns:
        SprintFeatures con todas las features
    """
    angles = analysis['angles']
    position = analysis['position']
    
    # Determinar pierna delantera/trasera
    if angles['left_knee'] < angles['right_knee']:
        front_knee = angles['left_knee']
        rear_knee = angles['right_knee']
        front_hip = angles['left_hip']
        rear_hip = angles['right_hip']
        front_ankle = angles['left_ankle']
        rear_ankle = angles['right_ankle']
    else:
        front_knee = angles['right_knee']
        rear_knee = angles['left_knee']
        front_hip = angles['right_hip']
        rear_hip = angles['left_hip']
        front_ankle = angles['right_ankle']
        rear_ankle = angles['left_ankle']
    
    # Calcular features
    knee_diff = abs(front_knee - rear_knee)
    hip_diff = abs(front_hip - rear_hip)
    
    # Score de simetría (0-1, 1 = perfectamente simétrico)
    symmetry_score = 1.0 - (knee_diff + hip_diff) / 360.0
    
    # Features de posición
    height_ratio = position['hip_height']
    foot_distance = position['distance_between_feet']
    support_base = position['support_base']
    com_x = position['center_of_mass_x']
    
    # Datos corporales (LiDAR + manuales)
    body = body_measurements or {}
    athlete = athlete_data or {}
    
    return SprintFeatures(
        knee_angle_front=front_knee,
        knee_angle_rear=rear_knee,
        hip_angle_front=front_hip,
        hip_angle_rear=rear_hip,
        ankle_angle_front=front_ankle,
        ankle_angle_rear=rear_ankle,
        trunk_angle=angles['trunk'],
        knee_diff=knee_diff,
        hip_diff=hip_diff,
        symmetry_score=symmetry_score,
        height_ratio=height_ratio,
        foot_distance=foot_distance,
        support_base=support_base,
        center_of_mass_x=com_x,
        # Datos corporales
        height_cm=float(body.get('height_cm', 0)),
        weight_kg=float(athlete.get('weight_kg', 0)),
        leg_length_cm=float(body.get('leg_length_cm', 0)),
        arm_length_cm=float(body.get('arm_length_cm', 0)),
        torso_length_cm=float(body.get('torso_length_cm', 0)),
        foot_length_cm=float(body.get('foot_length_cm', 0)),
        shoulder_width_cm=float(body.get('shoulder_width_cm', 0)),
        age=int(athlete.get('age', 0)),
        sex=athlete.get('sex', 'M'),
    )


def predict_from_features(features: SprintFeatures) -> Prediction:
    """
    Genera predicciones basadas en features extraídas.
    
    Modelo heurístico (sin entrenamiento previo).
    Se puede reemplazar con modelo entrenado posteriormente.
    """
    errors = []
    recommendations = []
    score = 5.0  # Base
    
    # --- Evaluar Rodilla ---
    if 90 <= features.knee_angle_front <= 110:
        score += 1.0
    elif 80 <= features.knee_angle_front <= 120:
        score += 0.5
    else:
        errors.append("Rodilla delantera fuera de rango óptimo")
        recommendations.append("Ajusta la flexión de la rodilla delantera a 90-110°")
        score -= 1.0
    
    if 120 <= features.knee_angle_rear <= 140:
        score += 0.5
    elif 110 <= features.knee_angle_rear <= 150:
        score += 0.25
    else:
        errors.append("Rodilla trasera fuera de rango óptimo")
        recommendations.append("Ajusta la rodilla trasera a 120-140°")
        score -= 0.5
    
    # --- Evaluar Cadera ---
    if 45 <= features.hip_angle_front <= 65:
        score += 1.0
    elif 35 <= features.hip_angle_front <= 75:
        score += 0.5
    else:
        errors.append("Cadera delantera fuera de rango óptimo")
        recommendations.append("Flexiona más la cadera delantera (45-65°)")
        score -= 1.0
    
    if 80 <= features.hip_angle_rear <= 100:
        score += 0.5
    elif 70 <= features.hip_angle_rear <= 110:
        score += 0.25
    else:
        errors.append("Cadera trasera fuera de rango óptimo")
        recommendations.append("Ajusta la cadera trasera a 80-100°")
        score -= 0.5
    
    # --- Evaluar Tronco ---
    if 15 <= features.trunk_angle <= 30:
        score += 1.0
    elif 10 <= features.trunk_angle <= 40:
        score += 0.5
    else:
        errors.append("Inclinación del tronco incorrecta")
        if features.trunk_angle < 15:
            recommendations.append("Inclina más el tronco hacia adelante")
        else:
            recommendations.append("Endereza el tronco un poco")
        score -= 1.0
    
    # --- Evaluar Simetría ---
    if features.symmetry_score >= 0.85:
        score += 0.5
    elif features.symmetry_score >= 0.7:
        score += 0.25
    else:
        errors.append("Baja simetría entre piernas")
        recommendations.append("Busca mayor equilibrio entre ambas piernas")
        score -= 0.5
    
    # --- Evaluar Posición ---
    if 0.35 <= features.height_ratio <= 0.55:
        score += 0.5
    else:
        errors.append("Altura de cadera subóptima")
        recommendations.append("Ajusta la altura de la cadera")
        score -= 0.25
    
    # --- Evaluar Datos Corporales ---
    if features.height_cm > 0 and features.weight_kg > 0:
        # Relación fuerza/peso estimada
        bmi = features.weight_kg / ((features.height_cm / 100) ** 2)
        if 18 <= bmi <= 25:
            score += 0.5
        elif 16 <= bmi <= 28:
            score += 0.25
        else:
            errors.append("BMI fuera de rango óptimo para sprint")
            recommendations.append("Consulta con un nutricionista deportivo")
            score -= 0.25
        
        # Relación pierna/estatura
        if features.leg_length_cm > 0:
            leg_ratio = features.leg_length_cm / features.height_cm
            if 0.45 <= leg_ratio <= 0.55:
                score += 0.25  # piernas largas = ventaja
        
        # Ancho de hombros vs cadera (proporción atlética)
        if features.shoulder_width_cm > 0:
            shoulder_hip_ratio = features.shoulder_width_cm / (features.height_cm * 0.5)
            if shoulder_hip_ratio >= 1.2:
                score += 0.25  # hombros anchos = bueno para sprint
    
    # --- Evaluar Edad ---
    if features.age > 0:
        if 18 <= features.age <= 30:
            score += 0.25  # rango óptimo
        elif 15 <= features.age <= 35:
            score += 0.125
    
    # Normalizar score (1-10)
    score = max(1.0, min(10.0, score))
    
    # Estimar tiempo de reacción basado en calidad + datos corporales
    reaction_time = 0.25 - (score * 0.012)
    
    # Ajustar por peso (más peso = potencialmente más lento)
    if features.weight_kg > 80:
        reaction_time += 0.01
    elif features.weight_kg < 60:
        reaction_time -= 0.005
    
    # Confianza basada en simetría + completitud de datos
    confidence = features.symmetry_score * 0.5 + 0.3
    
    # Bonus por datos completos
    if features.height_cm > 0 and features.weight_kg > 0:
        confidence += 0.1
    if features.leg_length_cm > 0:
        confidence += 0.1
    
    confidence = min(1.0, confidence)
    
    # Agregar recomendaciones generales si no hay errores
    if not recommendations:
        recommendations.append("Tu posición es óptima. ¡Sigue así!")
    
    # Agregar recomendaciones basadas en datos corporales
    if features.height_cm > 180:
        recommendations.append("Tu estatura es una ventaja: aprovecha la longitud de zancada")
    elif features.height_cm < 165 and features.height_cm > 0:
        recommendations.append("Compensa con mayor cadencia de piernas")
    
    return Prediction(
        quality_score=round(score, 1),
        reaction_time=round(reaction_time, 3),
        confidence=round(confidence, 2),
        errors_detected=errors,
        recommendations=recommendations,
        features_used={
            'knee_front': features.knee_angle_front,
            'knee_rear': features.knee_angle_rear,
            'hip_front': features.hip_angle_front,
            'hip_rear': features.hip_angle_rear,
            'trunk': features.trunk_angle,
            'symmetry': features.symmetry_score,
            'height_cm': features.height_cm,
            'weight_kg': features.weight_kg,
            'leg_length_cm': features.leg_length_cm,
            'age': features.age,
        }
    )


def format_prediction(prediction: Prediction) -> str:
    """Formatea predicción para mostrar."""
    lines = []
    
    lines.append("=" * 50)
    lines.append("  PREDICCIÓN DE SPRINT")
    lines.append("=" * 50)
    lines.append("")
    
    # Score
    if prediction.quality_score >= 8:
        emoji = "🌟"
        msg = "Excelente"
    elif prediction.quality_score >= 6:
        emoji = "👍"
        msg = "Bueno"
    elif prediction.quality_score >= 4:
        emoji = "⚠️"
        msg = "Mejorable"
    else:
        emoji = "❌"
        msg = "Necesita ajustes"
    
    lines.append(f"  {emoji} Calidad: {prediction.quality_score}/10 ({msg})")
    lines.append(f"  ⏱️  Tiempo estimado: {prediction.reaction_time:.3f}s")
    lines.append(f"  📊 Confianza: {prediction.confidence*100:.0f}%")
    lines.append("")
    
    if prediction.errors_detected:
        lines.append("  🔍 Errores detectados:")
        for error in prediction.errors_detected:
            lines.append(f"     • {error}")
        lines.append("")
    
    lines.append("  💡 Recomendaciones:")
    for rec in prediction.recommendations:
        lines.append(f"     • {rec}")
    
    lines.append("")
    lines.append("=" * 50)
    
    return "\n".join(lines)


def analyze_video_and_predict(video_frames_dir: str, sample_rate: int = 10) -> List[Prediction]:
    """
    Analiza un video completo y genera predicciones por frame.
    
    Args:
        video_frames_dir: directorio con frames del video
        sample_rate: analizar cada N frames
    
    Returns:
        lista de predicciones
    """
    from pathlib import Path
    import cv2
    from src.pose import PoseDetector
    from src.analysis import analyze_sprint_start
    
    frames_path = Path(video_frames_dir)
    frames = sorted(list(frames_path.glob("frame_*.png")))
    
    predictions = []
    
    with PoseDetector(model_complexity=2) as detector:
        for i, frame_path in enumerate(frames):
            if i % sample_rate != 0:
                continue
            
            rgb = cv2.imread(str(frame_path))
            if rgb is None:
                continue
            
            results = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
            
            if results:
                landmarks = detector.get_landmarks_normalized(results)
                analysis = analyze_sprint_start(landmarks)
                features = extract_features_from_analysis(analysis)
                prediction = predict_from_features(features)
                prediction.frame_index = i
                predictions.append(prediction)
    
    return predictions


def summarize_predictions(predictions: List[Prediction]) -> Dict:
    """Resume múltiples predicciones."""
    if not predictions:
        return {}
    
    scores = [p.quality_score for p in predictions]
    times = [p.reaction_time for p in predictions]
    
    return {
        'n_frames': len(predictions),
        'quality_mean': float(np.mean(scores)),
        'quality_std': float(np.std(scores)),
        'quality_min': float(np.min(scores)),
        'quality_max': float(np.max(scores)),
        'reaction_time_mean': float(np.mean(times)),
        'reaction_time_std': float(np.std(times)),
        'best_frame': int(predictions[np.argmax(scores)].frame_index),
        'worst_frame': int(predictions[np.argmin(scores)].frame_index),
    }


if __name__ == "__main__":
    # Test con video de prueba
    predictions = analyze_video_and_predict("data/r3d_extracted", sample_rate=50)
    
    if predictions:
        # Mostrar mejor predicción
        best = max(predictions, key=lambda p: p.quality_score)
        print("\nMEJOR FRAME:")
        print(format_prediction(best))
        
        # Resumen
        summary = summarize_predictions(predictions)
        print(f"\nRESUMEN DEL VIDEO:")
        print(f"  Frames analizados: {summary['n_frames']}")
        print(f"  Calidad promedio: {summary['quality_mean']:.1f}/10")
        print(f"  Mejor frame: {summary['best_frame']}")
        print(f"  Peor frame: {summary['worst_frame']}")
