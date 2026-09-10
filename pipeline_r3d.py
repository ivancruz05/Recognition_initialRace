"""
Pipeline completo: .r3d → frames + depth → MediaPipe → keypoints 3D.
Integra el parser de Record3D con el sistema de pose detection y fusion.

Uso:
    python pipeline_r3d.py <archivo.r3d>
    python pipeline_r3d.py <archivo.r3d> --headless 10
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from r3d_parser import R3DParser
from src.pose import PoseDetector
from src.depth import sample_depth_neighborhood
from src.fusion import fuse_landmarks_with_depth
from src.ply import save_point_cloud
from src.measurements import estimate_all_distances, estimate_joint_angles


def run_pipeline(r3d_path: str, headless: int = None):
    """Ejecuta el pipeline completo con un archivo .r3d."""
    
    print("=" * 60)
    print("  Pipeline: .r3d → Pose Detection → Keypoints 3D")
    print("=" * 60)
    
    # 1. Parsear .r3d
    print("\n[1/5] Parseando archivo .r3d...")
    parser = R3DParser(r3d_path)
    info = parser.get_info()
    print(f"      Archivo: {info['file']}")
    print(f"      Tamaño: {info['size_mb']:.1f} MB")
    print(f"      Resolución: {info['width']}x{info['height']}")
    print(f"      Frames: {info['frame_count']}")
    
    # 2. Extraer frames
    print("\n[2/5] Extrayendo frames y depth maps...")
    frames, depths = parser.extract_all()
    print(f"      Frames extraídos: {len(frames)}")
    
    if not frames:
        print("      Error: No se encontraron frames.")
        return
    
    # 3. Configurar MediaPipe
    print("\n[3/5] Configurando MediaPipe Pose...")
    
    # 4. Procesar frames
    print(f"\n[4/5] Procesando {len(frames)} frames...")
    
    output_dir = Path("data/r3d_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_summary = []
    
    with PoseDetector(model_complexity=2) as detector:
        for i, (rgb, depth) in enumerate(zip(frames, depths)):
            # Detectar pose
            rgb_for_mediapipe = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
            results = detector.detect(rgb_for_mediapipe)
            
            frame_result = {
                'index': i,
                'has_pose': results is not None,
                'n_keypoints': 0,
                'distances': {},
                'angles': {}
            }
            
            if results:
                landmarks = detector.get_landmarks_normalized(results)
                n_visible = int(np.sum(landmarks[:, 3] > 0.5))
                frame_result['n_keypoints'] = n_visible
                
                # Fusionar con depth si está disponible
                if depth is not None:
                    fused = fuse_landmarks_with_depth(landmarks, depth, rgb.shape[1], rgb.shape[0])
                    
                    # Calcular distancias
                    h, w = rgb.shape[:2]
                    distances, ref = estimate_all_distances(landmarks, w, h)
                    frame_result['distances'] = distances
                    
                    # Calcular ángulos
                    angles = estimate_joint_angles(landmarks)
                    frame_result['angles'] = angles
                
                # Dibujar en frame
                annotated = rgb.copy()
                detector.draw_skeleton(annotated, results)
                
                # Info en pantalla
                cv2.putText(annotated, f"Frame {i} | Keypoints: {n_visible}/33",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Guardar frame anotado
                cv2.imwrite(str(output_dir / f"frame_{i:06d}.png"), annotated)
            
            results_summary.append(frame_result)
            
            # Mostrar progreso
            if (i + 1) % 10 == 0 or i == len(frames) - 1:
                print(f"      Procesados {i + 1}/{len(frames)} frames")
    
    # 5. Resumen
    print("\n[5/5] Resumen:")
    print("-" * 50)
    
    frames_with_pose = sum(1 for r in results_summary if r['has_pose'])
    total_keypoints = sum(r['n_keypoints'] for r in results_summary)
    avg_keypoints = total_keypoints / max(frames_with_pose, 1)
    
    print(f"  Frames totales: {len(results_summary)}")
    print(f"  Frames con pose: {frames_with_pose} ({frames_with_pose/len(results_summary)*100:.1f}%)")
    print(f"  Keypoints promedio: {avg_keypoints:.1f}/33")
    
    # Guardar resumen
    summary_path = output_dir / "summary.txt"
    with open(summary_path, 'w') as f:
        f.write(f"R3D Processing Summary\n")
        f.write(f"{'='*50}\n\n")
        f.write(f"Archivo: {r3d_path}\n")
        f.write(f"Frames totales: {len(results_summary)}\n")
        f.write(f"Frames con pose: {frames_with_pose}\n")
        f.write(f"Keypoints promedio: {avg_keypoints:.1f}\n\n")
        
        for r in results_summary:
            f.write(f"Frame {r['index']}: pose={'SI' if r['has_pose'] else 'NO'}, "
                   f"keypoints={r['n_keypoints']}\n")
    
    print(f"\n  Frames anotados guardados en: {output_dir}")
    print(f"  Resumen guardado en: {summary_path}")
    
    print("\n" + "=" * 60)
    print("  Pipeline completado")
    print("=" * 60)
    
    return results_summary


def run_gui(r3d_path: str):
    """Ejecuta el pipeline con visualización en tiempo real."""
    
    parser = R3DParser(r3d_path)
    frames, depths = parser.extract_all()
    
    if not frames:
        print("Error: No se encontraron frames.")
        return
    
    print(f"  Frames: {len(frames)}")
    print("  Presiona 'q' para salir, 'espacio' para pausar")
    
    with PoseDetector(model_complexity=2) as detector:
        frame_idx = 0
        paused = False
        
        while True:
            if not paused:
                rgb = frames[frame_idx % len(frames)]
                
                # Detectar pose
                rgb_for_mediapipe = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
                results = detector.detect(rgb_for_mediapipe)
                
                annotated = rgb.copy()
                if results:
                    detector.draw_skeleton(annotated, results)
                    landmarks = detector.get_landmarks_normalized(results)
                    n_visible = int(np.sum(landmarks[:, 3] > 0.5))
                    cv2.putText(annotated, f"Frame {frame_idx} | Keypoints: {n_visible}/33",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    cv2.putText(annotated, f"Frame {frame_idx} | Sin deteccion",
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.imshow("R3D Pipeline", annotated)
                frame_idx += 1
            
            key = cv2.waitKey(30 if not paused else 100) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                paused = not paused
            elif key == ord('r'):
                frame_idx = 0
            
            # Loop
            if frame_idx >= len(frames):
                frame_idx = 0
    
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline .r3d → Pose Detection")
    parser.add_argument("r3d_file", help="Ruta al archivo .r3d")
    parser.add_argument("--headless", type=int, metavar="N", 
                       help="Procesar N frames sin ventana")
    parser.add_argument("--gui", action="store_true", 
                       help="Mostrar visualización en tiempo real")
    
    args = parser.parse_args()
    
    if args.headless:
        run_pipeline(args.r3d_file, headless=args.headless)
    elif args.gui:
        run_gui(args.r3d_file)
    else:
        run_pipeline(args.r3d_file)
