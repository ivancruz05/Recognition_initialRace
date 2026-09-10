"""
Captura de video en tiempo real para verificar deteccion de keypoints.
Abre la camara, detecta pose con MediaPipe y muestra los landmarks en vivo.
"""

import cv2
import numpy as np
from cv.pose_detector import PoseDetector


def main():
    print("=" * 60)
    print("  Captura de Video - Verificacion de Keypoints")
    print("=" * 60)
    print("\nInstrucciones:")
    print("  - Presiona 'q' para salir")
    print("  - Presiona 's' para guardar un frame con landmarks")
    print("  - Presiona 'espacio' para pausar/reanudar")
    print()

    # Abrir camara (0 = camara por defecto)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: No se pudo abrir la camara.")
        print("Intentando con camara alternatives...")
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("Error: No se encontro camara disponible.")
        return

    # Obtener propiedades de la camara
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"Camara: {width}x{height} @ {fps:.1f} FPS")
    print("-" * 60)

    # Inicializar detector de pose
    with PoseDetector(model_complexity=1) as detector:
        frame_count = 0
        paused = False

        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("Error: No se pudo leer frame de la camara.")
                    break

                frame_count += 1

                # Convertir BGR a RGB para MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Detectar pose
                results = detector.detect(rgb_frame)

                # Dibujar landmarks si se detectaron
                if results:
                    detector.draw_landmarks(frame, results)

                    # Obtener landmarks normalizados
                    landmarks = detector.get_landmarks_normalized(results)

                    # Mostrar info en pantalla
                    n_visible = np.sum(landmarks[:, 3] > 0.5)
                    cv2.putText(
                        frame,
                        f"Keypoints: 33 ({n_visible} visibles)",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )

                    # Mostrar coordenadas del nose (landmark 0)
                    nose = landmarks[0]
                    cv2.putText(
                        frame,
                        f"Nose: ({nose[0]:.2f}, {nose[1]:.2f})",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        1,
                    )
                else:
                    cv2.putText(
                        frame,
                        "No se detectaron keypoints",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )

                # Mostrar frame number
                cv2.putText(
                    frame,
                    f"Frame: {frame_count}",
                    (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                )

                # Mostrar frame
                cv2.imshow("Captura de Video - Keypoints", frame)

            # Teclas
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                print(f"\nSaliendo... Frames procesados: {frame_count}")
                break

            elif key == ord("s"):
                # Guardar frame actual
                output_path = f"data/samples/captured_frame_{frame_count:04d}.png"
                cv2.imwrite(output_path, frame)
                print(f"Frame guardado: {output_path}")

            elif key == ord(" "):
                paused = not paused
                if paused:
                    print("Pausado (presiona espacio para reanudar)")
                else:
                    print("Reanudado")

    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    print("Camara liberada.")


if __name__ == "__main__":
    main()
