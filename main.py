"""Pipeline de Computer Vision para analisis de posicion de arranque (FASE 1).

Uso:
    python main.py                 # pipeline con datos sinteticos
    python main.py ruta/video.mp4  # pipeline con video real
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from src import landmarks as lm
from src.camera import VideoPlayer
from src.config import SAMPLES_DIR, ensure_dir
from src.depth import depth_map_to_point_cloud
from src.fusion import SensorFusion
from src.ply import save_ply
from src.pose import PoseDetector
from src.synthetic import generate_synthetic_frame, synthetic_landmarks_array

KEY_NAMES = [
    "nose", "left_shoulder", "right_shoulder",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
]

DISTANCES = [
    ("Hombro Izq - Hombro Der", "left_shoulder", "right_shoulder"),
    ("Cadera Izq - Cadera Der", "left_hip", "right_hip"),
    ("Rodilla Izq - Rodilla Der", "left_knee", "right_knee"),
    ("Tobillo Izq - Tobillo Der", "left_ankle", "right_ankle"),
    ("Cadera Izq - Rodilla Izq", "left_hip", "left_knee"),
    ("Rodilla Izq - Tobillo Izq", "left_knee", "left_ankle"),
    ("Cadera Der - Rodilla Der", "right_hip", "right_knee"),
    ("Rodilla Der - Tobillo Der", "right_knee", "right_ankle"),
]


def run_synthetic_pipeline():
    """Valida el pipeline completo: pose + fusion con depth sintetico."""
    print("=" * 60)
    print("  FASE 1: Pipeline de Computer Vision + LiDAR (Sintetico)")
    print("=" * 60)

    rgb_frame, depth_map = generate_synthetic_frame()
    print(f"  RGB: {rgb_frame.shape} | Depth: {depth_map.shape}")
    print(f"  Depth range: {depth_map.min():.2f} - {depth_map.max():.2f} m")

    with PoseDetector() as detector:
        results = detector.detect(cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB))
        if results is None:
            print("  Sin deteccion en frame sintetico; usando landmarks sinteticos.")
            landmarks = synthetic_landmarks_array()
        else:
            landmarks = detector.get_landmarks_normalized(results)
            n_visible = int((landmarks[:, 3] > 0.5).sum())
            print(f"  Landmarks detectados: 33 ({n_visible} visibles)")

    fusion = SensorFusion(depth_radius=2)
    fused = fusion.fuse(landmarks, depth_map, rgb_frame.shape[1], rgb_frame.shape[0])
    positions_3d = fused["positions_3d"]
    visibility = fused["visibility"]

    n_valid = int((~np.isnan(positions_3d[:, 0])).sum())
    print(f"  Posiciones 3D validas: {n_valid}/33")

    print("\n  Coordenadas 3D de landmarks clave (metros):")
    print("-" * 55)
    print(f"  {'Landmark':<20} {'X':>8} {'Y':>8} {'Z':>8} {'Vis':>6}")
    print("-" * 55)
    for name in KEY_NAMES:
        idx = lm.LANDMARKS[name]
        x, y, z = positions_3d[idx]
        vis = visibility[idx]
        if np.isnan(x):
            print(f"  {name:<20} {'N/A':>8} {'N/A':>8} {'N/A':>8} {vis:>6.2f}")
        else:
            print(f"  {name:<20} {x:>8.3f} {y:>8.3f} {z:>8.3f} {vis:>6.2f}")

    print(f"\n  Distancias reales entre landmarks:")
    print("-" * 45)
    for label, name_a, name_b in DISTANCES:
        dist = fusion.get_distance_between_points(
            positions_3d, lm.LANDMARKS[name_a], lm.LANDMARKS[name_b]
        )
        if np.isnan(dist):
            print(f"  {label:<30} {'N/A':>8}")
        else:
            print(f"  {label:<30} {dist:>7.3f} m")

    samples_dir = ensure_dir(SAMPLES_DIR)
    points, colors = depth_map_to_point_cloud(depth_map, rgb_frame)
    ply_path = save_ply(samples_dir / "synthetic_sprint.ply", points, colors)
    cv2.imwrite(str(samples_dir / "synthetic_frame.png"), rgb_frame)
    np.save(str(samples_dir / "synthetic_depth.npy"), depth_map)

    print(f"\n  Point cloud: {ply_path} ({len(points)} puntos)")
    print("  Frame y depth map guardados en data/samples/")
    print("\n" + "=" * 60)
    print("  FASE 1 COMPLETADA - Pipeline funcionando con datos sinteticos")
    print("=" * 60)


def run_video_pipeline(video_path):
    """Procesa un video real mostrando la deteccion de pose frame a frame."""
    with VideoPlayer(video_path) as player:
        info = player.info()
        print(f"  Video: {info['width']}x{info['height']} @ {info['fps']:.1f} FPS"
              f" ({info['frame_count']} frames)")

        with PoseDetector(model_complexity=1) as detector:
            frames = 0
            while True:
                ok, frame = player.read()
                if not ok:
                    break

                frames += 1
                results = detector.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if results:
                    detector.draw_landmarks(frame, results)

                cv2.imshow("Pipeline - Pose Detection", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        cv2.destroyAllWindows()
        print(f"  Frames procesados: {frames}")


def main():
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if not Path(video_path).exists():
            print(f"Error: archivo no encontrado: {video_path}")
            sys.exit(1)
        run_video_pipeline(video_path)
    else:
        run_synthetic_pipeline()


if __name__ == "__main__":
    main()