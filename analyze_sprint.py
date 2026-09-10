"""
Pipeline completo de análisis de posición de salida.
Procesa frames extraídos de .r3d y genera reporte de métricas.

Uso:
    python analyze_sprint.py data/r3d_extracted/
    python analyze_sprint.py data/r3d_extracted/ --report report.txt
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from src.pose import PoseDetector
from src.analysis import analyze_sprint_start, format_analysis_report


def analyze_video_frames(frames_dir: str, output_report: str = None, sample_rate: int = 1):
    """
    Analiza todos los frames de un directorio.
    
    Args:
        frames_dir: directorio con frames PNG
        output_report: ruta del reporte de salida
        sample_rate: analizar cada N frames (1 = todos)
    """
    frames_path = Path(frames_dir)
    frames = sorted(list(frames_path.glob("frame_*.png")))
    
    if not frames:
        print("Error: No se encontraron frames en el directorio.")
        return
    
    print(f"Directorio: {frames_path}")
    print(f"Total frames: {len(frames)}")
    print(f"Sample rate: cada {sample_rate} frames")
    print(f"Frames a analizar: {len(frames) // sample_rate}")
    print()
    
    # Analizar frames
    all_analyses = []
    
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
                analysis['frame_index'] = i
                analysis['frame_path'] = str(frame_path)
                all_analyses.append(analysis)
            
            if (i + 1) % 100 == 0:
                print(f"  Procesados {i + 1}/{len(frames)} frames")
    
    print(f"\nFrames analizados: {len(all_analyses)}")
    
    if not all_analyses:
        print("Error: No se pudo analizar ningún frame.")
        return
    
    # Calcular estadísticas
    stats = _calculate_statistics(all_analyses)
    
    # Generar reporte
    report = _generate_report(all_analyses, stats)
    
    # Guardar reporte
    if output_report:
        report_path = Path(output_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\nReporte guardado: {report_path}")
    
    # Guardar datos JSON
    json_path = frames_path / "analysis_results.json"
    _save_json(all_analyses, stats, json_path)
    print(f"Datos JSON guardados: {json_path}")
    
    # Imprimir resumen
    print("\n" + "=" * 60)
    print("RESUMEN DEL ANÁLISIS")
    print("=" * 60)
    print(report)


def _calculate_statistics(analyses: list) -> dict:
    """Calcula estadísticas de todos los análisis."""
    angles_keys = ['left_knee', 'right_knee', 'left_hip', 'right_hip', 
                   'left_ankle', 'right_ankle', 'trunk']
    
    stats = {
        'angles_mean': {},
        'angles_std': {},
        'angles_min': {},
        'angles_max': {},
        'quality_mean': 0,
        'quality_std': 0,
        'n_frames': len(analyses),
    }
    
    # Recopilar valores
    angle_values = {k: [] for k in angles_keys}
    quality_values = []
    
    for analysis in analyses:
        for key in angles_keys:
            angle_values[key].append(analysis['angles'][key])
        quality_values.append(analysis['quality_score'])
    
    # Calcular estadísticas
    for key in angles_keys:
        values = angle_values[key]
        stats['angles_mean'][key] = float(np.mean(values))
        stats['angles_std'][key] = float(np.std(values))
        stats['angles_min'][key] = float(np.min(values))
        stats['angles_max'][key] = float(np.max(values))
    
    stats['quality_mean'] = float(np.mean(quality_values))
    stats['quality_std'] = float(np.std(quality_values))
    
    return stats


def _generate_report(analyses: list, stats: dict) -> str:
    """Genera reporte de análisis."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("  REPORTE DE ANÁLISIS DE POSICIÓN DE SALIDA DE SPRINT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Frames analizados: {stats['n_frames']}")
    lines.append(f"  Calidad promedio: {stats['quality_mean']:.1f}/100 (±{stats['quality_std']:.1f})")
    lines.append("")
    
    # Ángulos promedio
    lines.append("📐 ÁNGULOS PROMEDIO:")
    lines.append("-" * 50)
    
    angle_names = {
        'left_knee': 'Rodilla izquierda',
        'right_knee': 'Rodilla derecha',
        'left_hip': 'Cadera izquierda',
        'right_hip': 'Cadera derecha',
        'left_ankle': 'Tobillo izquierdo',
        'right_ankle': 'Tobillo derecho',
        'trunk': 'Tronco',
    }
    
    for key, name in angle_names.items():
        mean = stats['angles_mean'][key]
        std = stats['angles_std'][key]
        min_val = stats['angles_min'][key]
        max_val = stats['angles_max'][key]
        lines.append(f"  {name:<20} {mean:6.1f}° ± {std:5.1f}°  [{min_val:.1f}° - {max_val:.1f}°]")
    
    lines.append("")
    
    # Comparación con rangos óptimos
    lines.append("🎯 COMPARACIÓN CON RANGOS ÓPTIMOS:")
    lines.append("-" * 50)
    
    optimal_ranges = {
        'left_knee': (90, 120, 'Rodilla izquierda'),
        'right_knee': (90, 120, 'Rodilla derecha'),
        'left_hip': (45, 90, 'Cadera izquierda'),
        'right_hip': (45, 90, 'Cadera derecha'),
        'trunk': (15, 45, 'Tronco'),
    }
    
    for key, (opt_min, opt_max, name) in optimal_ranges.items():
        mean = stats['angles_mean'][key]
        if opt_min <= mean <= opt_max:
            status = "✅ ÓPTIMO"
        elif opt_min - 15 <= mean <= opt_max + 15:
            status = "⚠️  ACEPCIONABLE"
        else:
            status = "❌ FUERA DE RANGO"
        lines.append(f"  {name:<20} {mean:6.1f}°  {status}  ({opt_min}-{opt_max}°)")
    
    lines.append("")
    
    # Recomendaciones generales
    lines.append("💡 RECOMENDACIONES GENERALES:")
    lines.append("-" * 50)
    
    avg_knee = (stats['angles_mean']['left_knee'] + stats['angles_mean']['right_knee']) / 2
    avg_hip = (stats['angles_mean']['left_hip'] + stats['angles_mean']['right_hip']) / 2
    trunk = stats['angles_mean']['trunk']
    
    if avg_knee < 90:
        lines.append("  • Aumentar flexión de rodillas para más potencia de impulso")
    elif avg_knee > 120:
        lines.append("  • Reducir extensión de rodillas para mejor control")
    
    if avg_hip < 45:
        lines.append("  • Abrir más el ángulo de cadera")
    elif avg_hip > 90:
        lines.append("  • Cerrar el ángulo de cadera")
    
    if trunk < 15:
        lines.append("  • Inclinar más el tronco hacia adelante")
    elif trunk > 45:
        lines.append("  • Enderezar el tronco ligeramente")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def _save_json(analyses: list, stats: dict, output_path: Path):
    """Guarda resultados en JSON."""
    data = {
        'statistics': stats,
        'frames': []
    }
    
    for analysis in analyses:
        frame_data = {
            'frame_index': analysis['frame_index'],
            'angles': analysis['angles'],
            'position': analysis['position'],
            'quality_score': analysis['quality_score'],
            'recommendations': analysis['recommendations'],
        }
        data['frames'].append(frame_data)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análisis de posición de salida de sprint")
    parser.add_argument("frames_dir", help="Directorio con frames PNG")
    parser.add_argument("--report", help="Ruta del reporte de salida")
    parser.add_argument("--sample", type=int, default=10, 
                       help="Analizar cada N frames (default: 10)")
    
    args = parser.parse_args()
    
    analyze_video_frames(args.frames_dir, args.report, args.sample)
