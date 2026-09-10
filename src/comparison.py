"""
Comparación de posición de salida con referencia óptima.
Basado en literatura de biomecánica de sprint:

Referencias:
- Mann, R. (2011). "The Mechanics of Sprinting and Hurdling"
- Mero, A. et al. (1992). "Force-time characteristics and running velocity"
- Harland, M. & Steele, J. (1997). "Biomechanics of the sprint start"

Posición óptima de salida (bloc de salida):
- Rodilla delantera: 90-110° (flexión)
- Rodilla trasera: 120-140° (flexión menor)
- Cadera delantera: 45-60° (flexión)
- Cadera trasera: 80-100°
- Tronco: 15-25° (inclinación hacia adelante)
- Ángulo del pie: 45-50° con el suelo
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OptimalPosition:
    """Posición óptima de referencia para salida de sprint."""
    # Ángulos óptimos (grados)
    front_knee_angle: float = 100.0    # Rodilla delantera
    rear_knee_angle: float = 130.0     # Rodilla trasera
    front_hip_angle: float = 52.5      # Cadera delantera
    rear_hip_angle: float = 90.0       # Cadera trasera
    trunk_angle: float = 20.0          # Inclinación del tronco
    
    # Tolerancias (±grados)
    knee_tolerance: float = 15.0
    hip_tolerance: float = 15.0
    trunk_tolerance: float = 10.0
    
    # Métricas de posición
    hip_height_ratio: float = 0.45     # Altura de cadera / altura total
    support_base_ratio: float = 0.35   # Base de soporte / altura total


# Referencia basada en literatura
OPTIMAL_SPRINT_START = OptimalPosition()


@dataclass
class ComparisonResult:
    """Resultado de comparación con referencia."""
    joint: str
    actual: float
    optimal: float
    error: float
    error_percent: float
    status: str  # 'optimal', 'acceptable', 'poor'
    recommendation: str


def compare_with_reference(analysis: Dict, 
                          reference: OptimalPosition = None) -> Dict:
    """
    Compara el análisis actual con la posición de referencia.
    
    Args:
        analysis: resultado de analyze_sprint_start()
        reference: posición óptima de referencia
    
    Returns:
        dict con comparación detallada
    """
    if reference is None:
        reference = OPTIMAL_SPRINT_START
    
    angles = analysis['angles']
    position = analysis['position']
    
    # Comparar ángulos
    comparisons = []
    
    # Rodilla: determinar cuál es delantera/trasera
    # En posición de salida, la pierna delantera tiene mayor flexión
    if angles['left_knee'] < angles['right_knee']:
        front_knee = angles['left_knee']
        rear_knee = angles['right_knee']
        front_leg = 'left'
    else:
        front_knee = angles['right_knee']
        rear_knee = angles['left_knee']
        front_leg = 'right'
    
    # Cadera correspondiente
    front_hip = angles[f'{front_leg}_hip']
    rear_hip = angles[f'{"right" if front_leg == "left" else "left"}_hip']
    
    # Comparar cada articulación
    comparisons.append(_compare_angle(
        'Rodilla delantera', front_knee, reference.front_knee_angle, reference.knee_tolerance
    ))
    comparisons.append(_compare_angle(
        'Rodilla trasera', rear_knee, reference.rear_knee_angle, reference.knee_tolerance
    ))
    comparisons.append(_compare_angle(
        'Cadera delantera', front_hip, reference.front_hip_angle, reference.hip_tolerance
    ))
    comparisons.append(_compare_angle(
        'Cadera trasera', rear_hip, reference.rear_hip_angle, reference.hip_tolerance
    ))
    comparisons.append(_compare_angle(
        'Tronco', angles['trunk'], reference.trunk_angle, reference.trunk_tolerance
    ))
    
    # Calcular puntuación general
    overall_score = _calculate_overall_score(comparisons)
    
    # Generar recomendaciones prioritarias
    priorities = _prioritize_recommendations(comparisons)
    
    return {
        'comparisons': comparisons,
        'overall_score': overall_score,
        'front_leg': front_leg,
        'priorities': priorities,
        'reference_used': reference,
    }


def _compare_angle(name: str, actual: float, optimal: float, 
                   tolerance: float) -> ComparisonResult:
    """Compara un ángulo actual con el óptimo."""
    error = actual - optimal
    error_percent = abs(error) / optimal * 100
    
    if abs(error) <= tolerance * 0.5:
        status = 'optimal'
        recommendation = f"{name}: dentro del rango óptimo"
    elif abs(error) <= tolerance:
        status = 'acceptable'
        direction = "mayor" if error > 0 else "menor"
        recommendation = f"{name}: {direction} de lo óptimo ({abs(error):.1f}°)"
    else:
        status = 'poor'
        direction = "mayor" if error > 0 else "menor"
        recommendation = f"{name}: necesita ajuste significativo ({abs(error):.1f}° {direction})"
    
    return ComparisonResult(
        joint=name,
        actual=actual,
        optimal=optimal,
        error=error,
        error_percent=error_percent,
        status=status,
        recommendation=recommendation,
    )


def _calculate_overall_score(comparisons: List[ComparisonResult]) -> float:
    """Calcula puntuación general (0-100)."""
    scores = []
    
    for comp in comparisons:
        if comp.status == 'optimal':
            scores.append(100)
        elif comp.status == 'acceptable':
            # Penalizar proporcionalmente al error
            score = max(0, 100 - comp.error_percent * 2)
            scores.append(score)
        else:
            # Penalizar más fuertemente
            score = max(0, 100 - comp.error_percent * 3)
            scores.append(score)
    
    return float(np.mean(scores))


def _prioritize_recommendations(comparisons: List[ComparisonResult]) -> List[Dict]:
    """Prioriza las recomendaciones por importancia."""
    priorities = []
    
    for comp in sorted(comparisons, key=lambda x: abs(x.error_percent), reverse=True):
        if comp.status != 'optimal':
            priority = 'alta' if comp.status == 'poor' else 'media'
            priorities.append({
                'joint': comp.joint,
                'priority': priority,
                'current': comp.actual,
                'target': comp.optimal,
                'error': comp.error,
                'recommendation': comp.recommendation,
            })
    
    return priorities


def format_comparison_report(comparison: Dict) -> str:
    """Formatea reporte de comparación."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("  COMPARACIÓN CON POSICIÓN ÓPTIMA DE REFERENCIA")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Pierna delantera: {comparison['front_leg'].upper()}")
    lines.append(f"  Puntuación general: {comparison['overall_score']:.1f}/100")
    lines.append("")
    
    # Tabla de comparación
    lines.append("📐 COMPARACIÓN DE ÁNGULOS:")
    lines.append("-" * 70)
    lines.append(f"  {'Articulación':<20} {'Actual':>8} {'Óptimo':>8} {'Error':>8} {'Estado':>12}")
    lines.append("-" * 70)
    
    for comp in comparison['comparisons']:
        status_icon = {'optimal': '✅', 'acceptable': '⚠️', 'poor': '❌'}[comp.status]
        lines.append(
            f"  {comp.joint:<20} {comp.actual:>7.1f}° {comp.optimal:>7.1f}° "
            f"{comp.error:>+7.1f}° {status_icon} {comp.status:>10}"
        )
    
    lines.append("-" * 70)
    lines.append("")
    
    # Recomendaciones prioritarias
    lines.append("🎯 RECOMENDACIONES PRIORITARIAS:")
    lines.append("-" * 70)
    
    for i, rec in enumerate(comparison['priorities'][:3], 1):
        priority_icon = '🔴' if rec['priority'] == 'alta' else '🟡'
        lines.append(f"  {priority_icon} {i}. {rec['recommendation']}")
        lines.append(f"     Actual: {rec['current']:.1f}° → Objetivo: {rec['target']:.1f}°")
    
    lines.append("")
    
    # Resumen
    optimal_count = sum(1 for c in comparison['comparisons'] if c.status == 'optimal')
    acceptable_count = sum(1 for c in comparison['comparisons'] if c.status == 'acceptable')
    poor_count = sum(1 for c in comparison['comparisons'] if c.status == 'poor')
    
    lines.append("📊 RESUMEN:")
    lines.append(f"  ✅ Óptimos: {optimal_count}/5")
    lines.append(f"  ⚠️  Acepcionables: {acceptable_count}/5")
    lines.append(f"  ❌ Necesitan ajuste: {poor_count}/5")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    from src.analysis import analyze_sprint_start
    import cv2
    from src.pose import PoseDetector
    
    frame_path = "data/r3d_extracted/frame_000100.png"
    rgb = cv2.imread(frame_path)
    
    with PoseDetector(model_complexity=2) as detector:
        results = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
        
        if results:
            landmarks = detector.get_landmarks_normalized(results)
            analysis = analyze_sprint_start(landmarks)
            comparison = compare_with_reference(analysis)
            print(format_comparison_report(comparison))
