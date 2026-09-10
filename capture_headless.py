"""
Captura de video headless - guarda frames con keypoints detectados.
Para verificar que MediaPipe funciona sin necesidad de ventana grafica.
"""

import cv2
import numpy as np
from pathlib import Path
from cv.pose_detector import PoseDetector


def capture_frames(n_frames=5, output_dir="data/samples"):
    """Captura frames de la camara y guarda con landmarks dibujados."""
    print("=" * 60)
    print("  Captura Headless - Verificacion de Keypoints")
    print("=" * 60)

    # Crear directorio de salida
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Abrir camara
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la camara.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"\nCamara: {width}x{height} @ {fps:.1f} FPS")
    print(f"Capturando {n_frames} frames...\n")

    # Inicializar detector de pose
    with PoseDetector(model_complexity=1) as detector:
        frames_captured = 0
        frames_with_pose = 0

        while frames_captured < n_frames:
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo leer frame.")
                break

            frames_captured += 1

            # Detectar pose
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = detector.detect(rgb_frame)

            # Crear copia para dibujar
            frame_annotated = frame.copy()

            if results:
                frames_with_pose += 1
                detector.draw_landmarks(frame_annotated, results)

                # Obtener landmarks
                landmarks = detector.get_landmarks_normalized(results)
                n_visible = np.sum(landmarks[:, 3] > 0.5)

                # Info en pantalla
                cv2.putText(
                    frame_annotated,
                    f"Keypoints: 33 ({n_visible} visibles)",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )

                # Mostrar coordenadas clave
                key_points = [
                    ("Nose", 0), ("L_Shoulder", 11), ("R_Shoulder", 12),
                    ("L_Hip", 23), ("R_Hip", 24), ("L_Knee", 25), ("R_Knee", 26),
                    ("L_Ankle", 27), ("R_Ankle", 28),
                ]

                y_offset = 60
                for name, idx in key_points:
                    x, y, z, vis = landmarks[idx]
                    text = f"{name}: ({x:.2f}, {y:.2f}) vis={vis:.2f}"
                    cv2.putText(
                        frame_annotated,
                        text,
                        (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )
                    y_offset += 20

                print(f"  Frame {frames_captured}: {n_visible} keypoints visibles")
            else:
                cv2.putText(
                    frame_annotated,
                    "No keypoints detected",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )
                print(f"  Frame {frames_captured}: Sin deteccion")

            # Guardar frame con anotaciones
            output_file = output_path / f"captured_{frames_captured:04d}.png"
            cv2.imwrite(str(output_file), frame_annotated)

            # Esperar un poco entre frames
            cv2.waitKey(500)

    # Guardar tambien el frame sin anotaciones para referencia
    cap.release()

    print("\n" + "=" * 60)
    print(f"  Resultados:")
    print(f"    Frames capturados: {frames_captured}")
    print(f"    Frames con pose:  {frames_with_pose}")
    print(f"    Tasa de exito:    {frames_with_pose/max(frames_captured,1)*100:.1f}%")
    print(f"    Guardados en:     {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    capture_frames(n_frames=5)
