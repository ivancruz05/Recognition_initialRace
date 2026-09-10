"""
Análisis automático de sprint.
Sube un video (.r3d o .mp4) y obtén predicciones automáticamente.

Uso:
    python auto_analyze.py video.r3d
    python auto_analyze.py video.mp4
    python auto_analyze.py data/videos/
    python auto_analyze.py video.r3d --athlete '{"weight_kg": 75, "age": 24, "sex": "M"}'
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np

from r3d_parser import R3DParser
from src.pose import PoseDetector
from src.analysis import analyze_sprint_start
from src.comparison import compare_with_reference
from src.ml_analysis import (
    extract_features_from_analysis,
    predict_from_features,
    format_prediction,
    summarize_predictions,
)
from src.body_measurement import estimate_body_measurements_from_landmarks


def auto_analyze(input_path: str, output_dir: str = None, athlete_data: dict = None):
    """
    Análisis automático de un video de sprint.
    
    Args:
        input_path: ruta al video (.r3d, .mp4, .mov) o directorio de frames
        output_dir: directorio de salida para resultados
        athlete_data: datos del atleta (weight_kg, age, sex, height_cm opcional)
    """
    input_path = Path(input_path)
    
    if output_dir is None:
        output_dir = Path("data/analysis_output") / datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  ANÁLISIS AUTOMÁTICO DE SPRINT")
    print("=" * 60)
    print(f"\n  Entrada: {input_path}")
    print(f"  Salida: {output_dir}")
    
    if athlete_data:
        print(f"\n  📋 DATOS DEL ATLETA:")
        for key, value in athlete_data.items():
            print(f"     {key}: {value}")
    print()
    
    # Determinar tipo de entrada
    r3d_parser = None
    if input_path.suffix == '.r3d':
        frames = _process_r3d(input_path, output_dir)
        r3d_parser = R3DParser(str(input_path))
    elif input_path.suffix in ['.mp4', '.mov', '.avi']:
        frames = _process_video(input_path, output_dir)
    elif input_path.is_dir():
        frames = list(sorted(input_path.glob("frame_*.png")))
    else:
        print("Error: Formato no soportado. Usa .r3d, .mp4, .mov o directorio de frames.")
        return
    
    if not frames:
        print("Error: No se pudieron obtener frames.")
        return
    
    print(f"  Frames a analizar: {len(frames)}\n")
    
    # Analizar frames
    results = _analyze_frames(frames, output_dir, athlete_data, r3d_parser=r3d_parser)
    
    # Generar reporte
    _generate_report(results, output_dir, athlete_data)
    
    print("\n" + "=" * 60)
    print("  ANÁLISIS COMPLETADO")
    print("=" * 60)
    print(f"\n  Resultados guardados en: {output_dir}")
    print(f"  Reporte: {output_dir / 'report.txt'}")
    print(f"  Datos: {output_dir / 'results.json'}")


def _process_r3d(r3d_path: Path, output_dir: Path) -> list:
    """Procesa archivo .r3d y extrae frames."""
    print("  Procesando archivo .r3d...")
    
    parser = R3DParser(str(r3d_path))
    info = parser.get_info()
    print(f"    Tamaño: {info['size_mb']:.1f} MB")
    print(f"    Frames RGB: {info['rgb_frames']}")
    
    frames_dir = output_dir / "frames"
    parser.save_frames(str(frames_dir))
    
    return sorted(list(frames_dir.glob("frame_*.png")))


def _process_video(video_path: Path, output_dir: Path) -> list:
    """Procesa video (.mp4, .mov) y extrae frames."""
    print("  Procesando video...")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print("    Error: No se pudo abrir el video.")
        return []
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"    FPS: {fps:.1f}")
    print(f"    Resolución: {width}x{height}")
    print(f"    Frames totales: {frame_count}")
    
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Extraer frames (cada 5 frames paraahorrar tiempo)
    frame_idx = 0
    saved_count = 0
    frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % 5 == 0:
            frame_path = frames_dir / f"frame_{saved_count:06d}.png"
            cv2.imwrite(str(frame_path), frame)
            frames.append(frame_path)
            saved_count += 1
        
        frame_idx += 1
    
    cap.release()
    print(f"    Frames guardados: {saved_count}")
    
    return frames


def _analyze_frames(frames: list, output_dir: Path, athlete_data: dict = None, r3d_parser=None) -> dict:
    """Analiza todos los frames y genera predicciones con datos corporales y LiDAR."""
    print("  Analizando frames...\n")
    
    all_results = []
    
    # Estatura conocida para calibrar LiDAR (opcional)
    known_height = athlete_data.get('height_cm') if athlete_data else None
    
    with PoseDetector(model_complexity=2) as detector:
        for i, frame_path in enumerate(frames):
            rgb = cv2.imread(str(frame_path))
            if rgb is None:
                continue
            
            results = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
            
            if results:
                landmarks = detector.get_landmarks_normalized(results)
                
                # Análisis biomecánico
                analysis = analyze_sprint_start(landmarks)
                
                # Comparación con referencia
                comparison = compare_with_reference(analysis)
                
                # Obtener depth map si está disponible
                depth_map = None
                if r3d_parser is not None:
                    try:
                        _, depth_map, _ = r3d_parser.extract_frame(i)
                    except:
                        pass
                
                # Medición corporal con LiDAR (usando depth map real)
                body_measurements = estimate_body_measurements_from_landmarks(
                    landmarks,
                    known_height_cm=known_height,
                    depth_map=depth_map,
                    image_shape=rgb.shape
                )
                body_dict = {
                    'height_cm': body_measurements.height_cm,
                    'leg_length_cm': body_measurements.leg_length_cm,
                    'arm_length_cm': body_measurements.arm_length_cm,
                    'torso_length_cm': body_measurements.torso_length_cm,
                    'foot_length_cm': body_measurements.foot_length_cm,
                    'shoulder_width_cm': body_measurements.shoulder_width_cm,
                    'depth_valid_ratio': body_measurements.depth_valid_ratio,
                    'confidence': body_measurements.confidence,
                }
                
                # Features ML (keypoints + datos corporales + datos manuales)
                features = extract_features_from_analysis(
                    analysis,
                    body_measurements=body_dict,
                    athlete_data=athlete_data
                )
                prediction = predict_from_features(features)
                
                result = {
                    'frame_index': i,
                    'frame_path': str(frame_path),
                    'analysis': analysis,
                    'comparison': {
                        'overall_score': comparison['overall_score'],
                        'front_leg': comparison['front_leg'],
                    },
                    'body_measurements': body_dict,
                    'prediction': {
                        'quality_score': prediction.quality_score,
                        'reaction_time': prediction.reaction_time,
                        'confidence': prediction.confidence,
                        'errors': prediction.errors_detected,
                        'recommendations': prediction.recommendations,
                    },
                }
                all_results.append(result)
            
            if (i + 1) % 50 == 0:
                print(f"    Procesados {i + 1}/{len(frames)} frames")
    
    print(f"    Total frames analizados: {len(all_results)}")
    
    return {
        'frames': all_results,
        'athlete_data': athlete_data,
        'summary': summarize_predictions(
            [_dict_to_prediction(r['prediction'], r['frame_index']) for r in all_results]
        ),
    }


def _dict_to_prediction(pred_dict: dict, frame_index: int):
    """Convierte dict a Prediction para summarize_predictions."""
    from src.ml_analysis import Prediction
    p = Prediction(
        quality_score=pred_dict['quality_score'],
        reaction_time=pred_dict['reaction_time'],
        confidence=pred_dict['confidence'],
        errors_detected=pred_dict['errors'],
        recommendations=pred_dict['recommendations'],
        features_used={},
    )
    p.frame_index = frame_index
    return p


def _generate_report(results: dict, output_dir: Path, athlete_data: dict = None):
    """Genera reporte de análisis con datos corporales."""
    summary = results['summary']
    frames = results['frames']
    
    lines = []
    
    lines.append("=" * 60)
    lines.append("  REPORTE DE ANÁLISIS DE SPRINT")
    lines.append("=" * 60)
    lines.append(f"\n  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Frames analizados: {summary.get('n_frames', 0)}")
    
    # Datos del atleta
    if athlete_data:
        lines.append("")
        lines.append("  📋 DATOS DEL ATLETA:")
        if 'weight_kg' in athlete_data:
            lines.append(f"     Peso: {athlete_data['weight_kg']} kg")
        if 'age' in athlete_data:
            lines.append(f"     Edad: {athlete_data['age']} años")
        if 'sex' in athlete_data:
            lines.append(f"     Sexo: {athlete_data['sex']}")
        if 'height_cm' in athlete_data:
            lines.append(f"     Estatura: {athlete_data['height_cm']} cm (ingresada)")
    
    # Mediciones LiDAR (promedio del mejor frame)
    best_frame = max(frames, key=lambda f: f['prediction']['quality_score'])
    if 'body_measurements' in best_frame:
        body = best_frame['body_measurements']
        if body.get('height_cm', 0) > 0:
            lines.append("")
            lines.append("  📏 MEDICIONES LIDAR (mejor frame):")
            lines.append(f"     Estatura: {body['height_cm']:.1f} cm")
            lines.append(f"     Pierna: {body['leg_length_cm']:.1f} cm")
            lines.append(f"     Brazo: {body['arm_length_cm']:.1f} cm")
            lines.append(f"     Torso: {body['torso_length_cm']:.1f} cm")
            lines.append(f"     Pie: {body['foot_length_cm']:.1f} cm")
            lines.append(f"     Hombros: {body['shoulder_width_cm']:.1f} cm")
    
    lines.append("")
    
    # Resumen de calidad
    lines.append("  📊 CALIDAD PROMEDIO:")
    lines.append(f"     Score: {summary.get('quality_mean', 0):.1f}/10")
    lines.append(f"     Mejor: {summary.get('quality_max', 0):.1f}/10 (frame {summary.get('best_frame', 0)})")
    lines.append(f"     Peor: {summary.get('quality_min', 0):.1f}/10 (frame {summary.get('worst_frame', 0)})")
    lines.append("")
    
    # Tiempo de reacción
    lines.append("  ⏱️  TIEMPO ESTIMADO:")
    lines.append(f"     Promedio: {summary.get('reaction_time_mean', 0):.3f}s")
    lines.append(f"     Mejor: {min(f['prediction']['reaction_time'] for f in frames):.3f}s")
    lines.append("")
    
    # Velocidad estimada (2 metros)
    best_reaction = min(f['prediction']['reaction_time'] for f in frames)
    est_velocity = 2.0 / best_reaction if best_reaction > 0 else 0
    lines.append("  🚀 VELOCIDAD ESTIMADA (2m):")
    lines.append(f"     Mejor: {est_velocity:.2f} m/s")
    lines.append(f"     Tiempo 2m: {best_reaction:.3f}s")
    lines.append("")
    
    # Mejor análisis
    lines.append("  🏆 MEJOR ANÁLISIS:")
    lines.append(f"     Frame: {best_frame['frame_index']}")
    lines.append(f"     Calidad: {best_frame['prediction']['quality_score']}/10")
    lines.append(f"     Tiempo: {best_frame['prediction']['reaction_time']:.3f}s")
    lines.append(f"     Pierna delantera: {best_frame['comparison']['front_leg'].upper()}")
    lines.append("")
    
    # Errores más comunes
    error_counts = {}
    for frame in frames:
        for error in frame['prediction']['errors']:
            error_counts[error] = error_counts.get(error, 0) + 1
    
    if error_counts:
        lines.append("  🔍 ERRORES MÁS COMUNES:")
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(frames) * 100
            lines.append(f"     • {error} ({pct:.0f}%)")
        lines.append("")
    
    # Recomendaciones principales
    rec_counts = {}
    for frame in frames:
        for rec in frame['prediction']['recommendations']:
            rec_counts[rec] = rec_counts.get(rec, 0) + 1
    
    if rec_counts:
        lines.append("  💡 RECOMENDACIONES PRINCIPALES:")
        for rec, count in sorted(rec_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = count / len(frames) * 100
            lines.append(f"     • {rec} ({pct:.0f}%)")
    
    lines.append("")
    lines.append("=" * 60)
    
    report = "\n".join(lines)
    
    # Guardar reporte
    with open(output_dir / "report.txt", 'w') as f:
        f.write(report)
    
    # Guardar datos JSON
    with open(output_dir / "results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Imprimir
    print("\n" + report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análisis automático de sprint")
    parser.add_argument("input", help="Video (.r3d, .mp4, .mov) o directorio de frames")
    parser.add_argument("--output", help="Directorio de salida")
    parser.add_argument(
        "--athlete",
        help='Datos del atleta en JSON: \'{"weight_kg": 75, "age": 24, "sex": "M", "height_cm": 175}\'',
        type=str
    )
    
    args = parser.parse_args()
    
    athlete_data = None
    if args.athlete:
        try:
            athlete_data = json.loads(args.athlete)
        except json.JSONDecodeError:
            print("Error: Formato JSON inválido para --athlete")
            sys.exit(1)
    
    auto_analyze(args.input, args.output, athlete_data)
