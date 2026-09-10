"""
Captura con cámara de iPhone via macOS Continuity Camera.
Incluye detección de keypoints y mediciones de distancia/ángulos.
"""

import cv2
import numpy as np
from pathlib import Path
from cv.pose_detector import PoseDetector
from camera_measurements import (
    estimate_all_distances,
    estimate_joint_angles,
    REFERENCE_DISTANCES,
)


def find_iphone_camera():
    """Busca la cámara del iPhone entre los dispositivos disponibles."""
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            # iPhone cameras typically have higher resolution
            # and are usually index 1 when FaceTime is 0
            if i > 0 and w >= 1920:
                cap.release()
                return i
            cap.release()
    return None


def run_iphone_capture():
    """Ejecuta captura con cámara de iPhone."""
    print("=" * 60)
    print("  Captura con iPhone - Keypoints + Mediciones")
    print("=" * 60)

    # Buscar iPhone camera
    iphone_index = find_iphone_camera()

    if iphone_index is not None:
        print(f"\n  ✅ iPhone detectado en índice {iphone_index}")
        camera_index = iphone_index
    else:
        print("\n  ⚠️  iPhone no detectado, usando FaceTime HD")
        print("  Para usar iPhone:")
        print("    1. Conecta iPhone por USB")
        print("    2. Asegúrate que macOS Continuity Camera esté activo")
        print("    3. iPhone debe estar desbloqueado")
        camera_index = 0

    # Abrir cámara
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("  Error: No se pudo abrir la cámara.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"  Resolución: {width}x{height} @ {fps:.1f} FPS")
    print(f"\n  Controles:")
    print(f"    'q'     - Salir")
    print(f"    's'     - Guardar frame con keypoints")
    print(f"    'espacio' - Pausar/Reanudar")
    print(f"    '1-3'   - Cambiar modo de visualización")
    print()

    output_dir = Path("data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    view_mode = 1  # 1=keypoints, 2=distancias, 3=angulos

    with PoseDetector(model_complexity=1) as detector:
        frame_count = 0
        paused = False

        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = detector.detect(rgb)
                frame_annotated = frame.copy()

                if results:
                    landmarks = detector.get_landmarks_normalized(results)
                    n_visible = int(np.sum(landmarks[:, 3] > 0.5))

                    # Dibujar keypoints
                    for idx in range(33):
                        x = int(landmarks[idx, 0] * width)
                        y = int(landmarks[idx, 1] * height)
                        vis = landmarks[idx, 3]
                        color = (0, 255, 0) if vis > 0.5 else (0, 0, 255)
                        cv2.circle(frame_annotated, (x, y), 5, color, -1)

                    # Dibujar conexiones
                    connections = [
                        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
                        (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
                        (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32),
                    ]
                    for a, b in connections:
                        if landmarks[a, 3] > 0.5 and landmarks[b, 3] > 0.5:
                            xa = int(landmarks[a, 0] * width)
                            ya = int(landmarks[a, 1] * height)
                            xb = int(landmarks[b, 0] * width)
                            yb = int(landmarks[b, 1] * height)
                            cv2.line(frame_annotated, (xa, ya), (xb, yb), (0, 255, 0), 2)

                    # Panel de información
                    y_pos = 25
                    cv2.putText(frame_annotated, f"iPhone Camera | Keypoints: {n_visible}/33",
                                (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    y_pos += 25

                    # Modo 1: Keypoints info
                    if view_mode == 1:
                        cv2.putText(frame_annotated, f"Modo: Keypoints",
                                    (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        y_pos += 25

                        # Mostrar keypoints visibles
                        key_points = [
                            ("Nose", 0), ("L_Shoulder", 11), ("R_Shoulder", 12),
                            ("L_Elbow", 13), ("R_Elbow", 14),
                            ("L_Hip", 23), ("R_Hip", 24),
                            ("L_Knee", 25), ("R_Knee", 26),
                            ("L_Ankle", 27), ("R_Ankle", 28),
                        ]
                        for name, idx in key_points:
                            x, y, z, vis = landmarks[idx]
                            status = "OK" if vis > 0.5 else "NO"
                            color = (0, 255, 0) if vis > 0.5 else (0, 0, 255)
                            text = f"{name}: ({x:.2f}, {y:.2f}) [{status}]"
                            cv2.putText(frame_annotated, text,
                                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                            y_pos += 18

                    # Modo 2: Distancias
                    elif view_mode == 2:
                        distances, ref_used = estimate_all_distances(landmarks, width, height)
                        cv2.putText(frame_annotated, f"Modo: Distancias",
                                    (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        y_pos += 25

                        if distances:
                            cv2.putText(frame_annotated, f"Ref: {ref_used}",
                                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                            y_pos += 20
                            for name, dist in sorted(distances.items()):
                                text = f"{name}: {dist:.3f}m"
                                cv2.putText(frame_annotated, text,
                                            (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                                y_pos += 18
                        else:
                            cv2.putText(frame_annotated, "Alejate para ver piernas",
                                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                    # Modo 3: Ángulos
                    elif view_mode == 3:
                        angles = estimate_joint_angles(landmarks)
                        cv2.putText(frame_annotated, f"Modo: Angulos",
                                    (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        y_pos += 25

                        if angles:
                            for name, angle in sorted(angles.items()):
                                text = f"{name}: {angle:.1f} grados"
                                cv2.putText(frame_annotated, text,
                                            (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
                                y_pos += 18
                        else:
                            cv2.putText(frame_annotated, "Alejate para ver piernas",
                                        (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                else:
                    cv2.putText(frame_annotated, "Sin deteccion",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                # Pie de página
                cv2.putText(frame_annotated, f"Frame: {frame_count} | Modo: {view_mode}/3 | q=salir s=guardar",
                            (10, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

                cv2.imshow("iPhone Sprint Analysis", frame_annotated)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            elif key == ord("s"):
                path = output_dir / f"iphone_{frame_count:04d}.png"
                cv2.imwrite(str(path), frame_annotated)
                print(f"  Guardado: {path}")
            elif key == ord(" "):
                paused = not paused
            elif key == ord("1"):
                view_mode = 1
            elif key == ord("2"):
                view_mode = 2
            elif key == ord("3"):
                view_mode = 3

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n  Frames procesados: {frame_count}")


if __name__ == "__main__":
    run_iphone_capture()
