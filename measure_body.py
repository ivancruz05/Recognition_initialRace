"""
Script simplificado para medir dimensiones corporales con LiDAR.

Uso:
    python measure_body.py <video.r3d> --height 179
    python measure_body.py <video.r3d>  # sin estatura conocida
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from r3d_parser import R3DParser
from src.pose import PoseDetector
from src.body_measurement import estimate_body_measurements_from_landmarks, format_measurements


def measure_video(video_path: str, known_height: float = None):
    """Mide dimensiones corporales de un video .r3d"""
    
    print(f"\n{'='*50}")
    print(f"  MEDICIÓN CORPORAL - LiDAR")
    print(f"{'='*50}\n")
    
    # Parse video
    parser = R3DParser(video_path)
    info = parser.get_info()
    
    print(f"📹 Video: {Path(video_path).name}")
    print(f"   Frames: {info['rgb_frames']}")
    print(f"   LiDAR: {'✓' if info['has_lzfse'] else '✗'}")
    print()
    
    # Analizar múltiples frames para obtener mejor estimación
    measurements_list = []
    
    with PoseDetector(model_complexity=2) as detector:
        # Muestrear frames evenly
        sample_indices = np.linspace(0, info['rgb_frames']-1, min(30, info['rgb_frames']), dtype=int)
        
        for frame_idx in sample_indices:
            rgb, depth, conf = parser.extract_frame(int(frame_idx))
            if rgb is None or depth is None:
                continue
            
            results = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
            if not results:
                continue
            
            landmarks = detector.get_landmarks_normalized(results)
            
            measurements = estimate_body_measurements_from_landmarks(
                landmarks,
                known_height_cm=known_height,
                depth_map=depth,
                image_shape=rgb.shape
            )
            
            if measurements.confidence > 0:
                measurements_list.append(measurements)
    
    if not measurements_list:
        print("❌ No se pudieron obtener mediciones")
        return
    
    # Promediar mediciones
    avg_measurements = type(measurements_list[0])(
        height_cm=np.mean([m.height_cm for m in measurements_list]),
        leg_length_cm=np.mean([m.leg_length_cm for m in measurements_list]),
        arm_length_cm=np.mean([m.arm_length_cm for m in measurements_list]),
        torso_length_cm=np.mean([m.torso_length_cm for m in measurements_list]),
        foot_length_cm=np.mean([m.foot_length_cm for m in measurements_list]),
        shoulder_width_cm=np.mean([m.shoulder_width_cm for m in measurements_list]),
        confidence=np.mean([m.confidence for m in measurements_list]),
        depth_valid_ratio=np.mean([m.depth_valid_ratio for m in measurements_list]),
    )
    
    # Mostrar resultados
    print(format_measurements(avg_measurements))
    
    print(f"\n📊 Frames analizados: {len(measurements_list)}")
    
    # Guardar resultados
    output_dir = Path("data/measurements")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{Path(video_path).stem}_measurements.json"
    with open(output_file, 'w') as f:
        json.dump({
            'video': video_path,
            'known_height_cm': known_height,
            'measurements': {
                'height_cm': avg_measurements.height_cm,
                'leg_length_cm': avg_measurements.leg_length_cm,
                'arm_length_cm': avg_measurements.arm_length_cm,
                'torso_length_cm': avg_measurements.torso_length_cm,
                'foot_length_cm': avg_measurements.foot_length_cm,
                'shoulder_width_cm': avg_measurements.shoulder_width_cm,
            },
            'confidence': avg_measurements.confidence,
            'frames_analyzed': len(measurements_list),
        }, f, indent=2)
    
    print(f"\n💾 Guardado en: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Medición corporal con LiDAR")
    parser.add_argument("video", help="Archivo .r3d a analizar")
    parser.add_argument("--height", type=float, help="Estatura conocida en cm (ej: 179)")
    
    args = parser.parse_args()
    
    if not Path(args.video).exists():
        print(f"❌ Archivo no encontrado: {args.video}")
        sys.exit(1)
    
    measure_video(args.video, args.height)


if __name__ == "__main__":
    main()
