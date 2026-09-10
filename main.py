"""
Pipeline de Computer Vision para analisis de posicion de arranque.
FASE 1: Video → OpenCV → Pose Estimation → Keypoints 3D con LiDAR depth.
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

from cv.video_reader import VideoReader
from cv.pose_detector import PoseDetector
from lidar.depth_utils import sample_depth_neighborhood, depth_map_to_point_cloud
from fusion.sensor_fusion import SensorFusion
from synthetic_data import (
    generate_skeleton_image,
    generate_depth_map,
    generate_synthetic_frame,
)


def run_synthetic_pipeline():
    """Ejecuta el pipeline completo con datos sinteticos."""
    print("=" * 60)
    print("  FASE 1: Pipeline de Computer Vision + LiDAR (Sintetico)")
    print("=" * 60)

    # 1. Generar frame sintetico
    print("\n[1/5] Generando frame sintetico...")
    rgb_frame, depth_map = generate_synthetic_frame(
        width=640, height=480, depth_width=256, depth_height=192
    )
    print(f"      RGB: {rgb_frame.shape} | Depth: {depth_map.shape}")
    print(f"      Depth range: {depth_map.min():.2f} - {depth_map.max():.2f} m")

    # 2. Detectar pose con MediaPipe
    print("\n[2/5] Detectando pose con MediaPipe...")
    rgb_for_mediapipe = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB)

    with PoseDetector() as detector:
        results = detector.detect(rgb_for_mediapipe)

        if results is None:
            print("      [!] No se detectaron landmarks. Usando posiciones sinteticas.")
            # Usar posiciones sinteticas como fallback
            landmarks_norm = _get_synthetic_landmarks()
        else:
            landmarks_norm = detector.get_landmarks_normalized(results)
            n_visible = np.sum(landmarks_norm[:, 3] > 0.5)
            print(f"      Landmarks detectados: 33 ({n_visible} visibles)")

    # 3. Fusionar landmarks con depth map
    print("\n[3/5] Fusionando landmarks + depth map...")
    fusion = SensorFusion(depth_radius=2)
    fused = fusion.fuse(landmarks_norm, depth_map, rgb_frame.shape[1], rgb_frame.shape[0])

    positions_3d = fused["positions_3d"]
    visibility = fused["visibility"]

    n_valid = np.sum(~np.isnan(positions_3d[:, 0]))
    print(f"      Posiciones 3D validas: {n_valid}/33")

    # 4. Mostrar coordenadas 3D de landmarks clave
    print("\n[4/5] Coordenadas 3D de landmarks clave (metros):")
    print("-" * 55)
    print(f"  {'Landmark':<20} {'X':>8} {'Y':>8} {'Z':>8} {'Vis':>6}")
    print("-" * 55)

    key_landmarks = {
        "nose": 0, "left_shoulder": 11, "right_shoulder": 12,
        "left_hip": 23, "right_hip": 24,
        "left_knee": 25, "right_knee": 26,
        "left_ankle": 27, "right_ankle": 28,
        "left_heel": 29, "right_heel": 30,
    }

    for name, idx in key_landmarks.items():
        x, y, z = positions_3d[idx]
        vis = visibility[idx]
        if np.isnan(x):
            print(f"  {name:<20} {'N/A':>8} {'N/A':>8} {'N/A':>8} {vis:>6.2f}")
        else:
            print(f"  {name:<20} {x:>8.3f} {y:>8.3f} {z:>8.3f} {vis:>6.2f}")

    # 5. Calcular distancias reales
    print("\n[5/5] Distancias reales entre landmarks:")
    print("-" * 45)

    distances = [
        ("Hombro Izq - Hombro Der", 11, 12),
        ("Cadera Izq - Cadera Der", 23, 24),
        ("Rodilla Izq - Rodilla Der", 25, 26),
        ("Tobillo Izq - Tobillo Der", 27, 28),
        ("Cadera Izq - Rodilla Izq", 23, 25),
        ("Rodilla Izq - Tobillo Izq", 25, 27),
        ("Cadera Der - Rodilla Der", 24, 26),
        ("Rodilla Der - Tobillo Der", 26, 28),
    ]

    for label, idx_a, idx_b in distances:
        dist = fusion.get_distance_between_points(positions_3d, idx_a, idx_b)
        if np.isnan(dist):
            print(f"  {label:<30} {'N/A':>8}")
        else:
            print(f"  {label:<30} {dist:>7.3f} m")

    # 6. Generar point cloud y guardar
    print("\n[ Bonus ] Generando point cloud...")
    points, colors = depth_map_to_point_cloud(depth_map, rgb_frame)

    output_dir = Path("data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    ply_path = output_dir / "synthetic_sprint.ply"
    _save_ply(ply_path, points, colors)
    print(f"      Point cloud guardada: {ply_path} ({len(points)} puntos)")

    # Guardar imagen con skeleton
    img_path = output_dir / "synthetic_frame.png"
    cv2.imwrite(str(img_path), rgb_frame)
    print(f"      Frame guardado: {img_path}")

    # Guardar depth map
    depth_path = output_dir / "synthetic_depth.npy"
    np.save(str(depth_path), depth_map)
    print(f"      Depth map guardado: {depth_path}")

    print("\n" + "=" * 60)
    print("  FASE 1 COMPLETADA - Pipeline funcionando con datos sinteticos")
    print("=" * 60)


def run_video_pipeline(video_path):
    """Ejecuta el pipeline con un video real."""
    print(f"\nProcesando video: {video_path}")

    reader = VideoReader(video_path)
    info = reader.get_info()
    print(f"FPS: {info['fps']:.1f} | Resolucion: {info['width']}x{info['height']}")
    print(f"Frames totales: {info['frame_count']} | Duracion: {info['duration_sec']:.2f}s")

    with PoseDetector(model_complexity=1) as detector:
        frame_idx = 0
        while reader.is_opened():
            ret, frame = reader.read_frame()
            if not ret:
                break

            # Detectar pose
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = detector.detect(rgb)

            if results:
                detector.draw_landmarks(frame, results)

            # Mostrar frame
            cv2.imshow("Pipeline - Pose Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            frame_idx += 1

    reader.release()
    cv2.destroyAllWindows()
    print(f"Procesados {frame_idx} frames.")


def _get_synthetic_landmarks():
    """Retorna landmarks sinteticos en formato normalizado (33, 4)."""
    from synthetic_data import STARTING_POSITION_LANDMARKS

    landmarks = np.zeros((33, 4))

    # Mapear posiciones conocidas
    name_to_idx = {
        "nose": 0, "left_shoulder": 11, "right_shoulder": 12,
        "left_elbow": 13, "right_elbow": 14,
        "left_wrist": 15, "right_wrist": 16,
        "left_hip": 23, "right_hip": 24,
        "left_knee": 25, "right_knee": 26,
        "left_ankle": 27, "right_ankle": 28,
        "left_heel": 29, "right_heel": 30,
        "left_foot_index": 31, "right_foot_index": 32,
    }

    for name, idx in name_to_idx.items():
        if name in STARTING_POSITION_LANDMARKS:
            x, y = STARTING_POSITION_LANDMARKS[name]
            landmarks[idx] = [x, y, 0.0, 1.0]

    # Interpolar landmarks faltantes
    _interpolate_landmarks(landmarks)

    return landmarks


def _interpolate_landmarks(landmarks):
    """Interpola landmarks faltantes basado en los conocidos."""
    # Hombros -> cuello (promedio)
    if np.any(landmarks[11]) and np.any(landmarks[12]):
        landmarks[1] = (landmarks[11] + landmarks[12]) / 2  # neck
        landmarks[1][3] = 1.0

    # Media cadera
    if np.any(landmarks[23]) and np.any(landmarks[24]):
        landmarks[22] = (landmarks[23] + landmarks[24]) / 2  # mid hip
        landmarks[22][3] = 1.0


def _save_ply(path, points, colors):
    """Guarda point cloud en formato PLY."""
    n = len(points)
    with open(path, "w") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        for i in range(n):
            r = int(colors[i, 0] * 255)
            g = int(colors[i, 1] * 255)
            b = int(colors[i, 2] * 255)
            f.write(f"{points[i, 0]:.4f} {points[i, 1]:.4f} {points[i, 2]:.4f} {r} {g} {b}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if Path(video_path).exists():
            run_video_pipeline(video_path)
        else:
            print(f"Error: archivo no encontrado: {video_path}")
            sys.exit(1)
    else:
        run_synthetic_pipeline()
