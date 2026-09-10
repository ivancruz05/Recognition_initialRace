"""
Pipeline completo de comparación con referencia óptima.
Procesa frames y genera reporte de desviaciones.

Uso:
    python compare_reference.py data/r3d_extracted/
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from src.pose import PoseDetector
from src.analysis import analyze_sprint_start
from src.comparison import compare_with_reference, format_comparison_report, OptimalPosition


def compare_all_frames(frames_dir: str, output_report: str = None, sample_rate: int = 10):
    """
    Compara todos los frames con la posición de referencia.
    """
    frames_path = Path(frames_dir)
    frames = sorted(list(frames_path.glob("frame_*.png")))
    
    if not frames:
        print("Error: No se encontraron frames.")
        return
    
    print(f"Comparando {len(frames) // sample_rate} frames con referencia óptima...\n")
    
    all_comparisons = []
    
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
                comparison = compare_with_reference(analysis)
                comparison['frame_index'] = i
                all_comparisons.append(comparison)
    
    print(f"Frames comparados: {len(all_comparisons)}")
    
    if not all_comparisons:
        print("Error: No se pudo comparar ningún frame.")
        return
    
    # Calcular estadísticas
    stats = _calculate_comparison_stats(all_comparisons)
    
    # Generar reporte
    report = _generate_comparison_report(all_comparisons, stats)
    
    # Guardar
    if output_report:
        with open(output_report, 'w') as f:
            f.write(report)
        print(f"Reporte guardado: {output_report}")
    
    # Guardar JSON
    json_path = frames_path / "comparison_results.json"
    _save_comparison_json(all_comparisons, stats, json_path)
    print(f"JSON guardado: {json_path}")
    
    print("\n" + report)


def _calculate_comparison_stats(comparisons: list) -> dict:
    """Calcula estadísticas de comparación."""
    joint_errors = {}
    
    for comp in comparisons:
        for c in comp['comparisons']:
            if c.joint not in joint_errors:
                joint_errors[c.joint] = []
            joint_errors[c.joint].append(abs(c.error))
    
    stats = {
        'n_frames': len(comparisons),
        'mean_errors': {},
        'std_errors': {},
        'scores': [c['overall_score'] for c in comparisons],
        'score_mean': 0,
        'score_std': 0,
    }
    
    for joint, errors in joint_errors.items():
        stats['mean_errors'][joint] = float(np.mean(errors))
        stats['std_errors'][joint] = float(np.std(errors))
    
    stats['score_mean'] = float(np.mean(stats['scores']))
    stats['score_std'] = float(np.std(stats['scores']))
    
    return stats


def _generate_comparison_report(comparisons: list, stats: dict) -> str:
    """Genera reporte consolidado de comparación."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("  REPORTE DE COMPARACIÓN CON REFERENCIA ÓPTIMA")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Frames analizados: {stats['n_frames']}")
    lines.append(f"  Puntuación promedio: {stats['score_mean']:.1f}/100 (±{stats['score_std']:.1f})")
    lines.append("")
    
    # Errores promedio por articulación
    lines.append("📐 ERROR PROMEDIO POR ARTICULACIÓN:")
    lines.append("-" * 60)
    lines.append(f"  {'Articulación':<25} {'Error medio':>12} {'Desviación':>12}")
    lines.append("-" * 60)
    
    for joint, error in sorted(stats['mean_errors'].items()):
        std = stats['std_errors'][joint]
        lines.append(f"  {joint:<25} {error:>10.1f}° ± {std:>8.1f}°")
    
    lines.append("-" * 60)
    lines.append("")
    
    # Distribución de estados
    optimal_total = 0
    acceptable_total = 0
    poor_total = 0
    
    for comp in comparisons:
        for c in comp['comparisons']:
            if c.status == 'optimal':
                optimal_total += 1
            elif c.status == 'acceptable':
                acceptable_total += 1
            else:
                poor_total += 1
    
    total = optimal_total + acceptable_total + poor_total
    
    lines.append("📊 DISTRIBUCIÓN DE ESTADOS:")
    lines.append("-" * 60)
    lines.append(f"  ✅ Óptimos:      {optimal_total:>4} ({optimal_total/total*100:.1f}%)")
    lines.append(f"  ⚠️  Acepcionables: {acceptable_total:>4} ({acceptable_total/total*100:.1f}%)")
    lines.append(f"  ❌ Pobres:       {poor_total:>4} ({poor_total/total*100:.1f}%)")
    lines.append("-" * 60)
    lines.append("")
    
    # Recomendaciones más frecuentes
    lines.append("🎯 RECOMENDACIONES MÁS FRECUENTES:")
    lines.append("-" * 60)
    
    recommendation_counts = {}
    for comp in comparisons:
        for p in comp['priorities']:
            key = p['joint']
            if key not in recommendation_counts:
                recommendation_counts[key] = 0
            recommendation_counts[key] += 1
    
    for joint, count in sorted(recommendation_counts.items(), 
                                key=lambda x: x[1], reverse=True)[:3]:
        pct = count / stats['n_frames'] * 100
        lines.append(f"  • {joint}: {count}/{stats['n_frames']} frames ({pct:.0f}%)")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def _save_comparison_json(comparisons: list, stats: dict, output_path: Path):
    """Guarda resultados en JSON."""
    data = {
        'statistics': stats,
        'comparisons': []
    }
    
    for comp in comparisons:
        comp_data = {
            'frame_index': comp['frame_index'],
            'overall_score': comp['overall_score'],
            'front_leg': comp['front_leg'],
            'joints': [{
                'name': c.joint,
                'actual': c.actual,
                'optimal': c.optimal,
                'error': c.error,
                'status': c.status,
            } for c in comp['comparisons']],
        }
        data['comparisons'].append(comp_data)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comparación con referencia óptima")
    parser.add_argument("frames_dir", help="Directorio con frames")
    parser.add_argument("--report", default="data/r3d_output/reference_comparison.txt")
    parser.add_argument("--sample", type=int, default=10)
    
    args = parser.parse_args()
    compare_all_frames(args.frames_dir, args.report, args.sample)
