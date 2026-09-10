"""
Captura interactiva con mejor visualizacion de keypoints.
Muestra keypoints coloreados por grupo (cara, torso, piernas).
"""

import cv2
import numpy as np
from pathlib import Path
from cv.pose_detector import PoseDetector


# Colores por grupo de keypoints
COLORS = {
    "face": (0, 255, 255),      # Amarillo
    "torso": (0, 200, 0),        # Verde
    "left_leg": (255, 100, 0),   # Naranja
    "right_leg": (0, 100, 255),  # Azul
}

GROUPS = {
    "face": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "torso": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
    "left_leg": [23, 25, 27, 29, 31],
    "right_leg": [24, 26, 28, 30, 32],
}


def main():
    print("=" * 60)
    print("  Captura Interactiva - Keypoints Coloreados")
    print("=" * 60)
    print("\n  Para ANALISIS DE SPRINT:")
    print("  - Alejate para que se vean las piernas completas")
    print("  - Vista lateral (de perfil) es ideal")
    print("  - Mantente en posicion de arranque 2-3 segundos")
    print()
    print("  Controles:")
    print("  - 'q': Salir")
    print("  - 's': Guardar frame con keypoints")
    print("  - 'espacio': Pausar/Reanudar")
    print("  - '1-5': Capturar frame automaticamente cada N segundos")
    print()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la camara.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  Camara: {width}x{height}\n")

    output_dir = Path("data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    with PoseDetector(model_complexity=1) as detector:
        frame_count = 0
        paused = False
        auto_capture = 0
        last_capture_time = 0

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

                    # Dibujar keypoints por grupo con colores distintos
                    for group_name, indices in GROUPS.items():
                        color = COLORS[group_name]
                        for idx in indices:
                            x = int(landmarks[idx, 0] * width)
                            y = int(landmarks[idx, 1] * height)
                            vis = landmarks[idx, 3]

                            if vis > 0.5:
                                cv2.circle(frame_annotated, (x, y), 6, color, -1)
                                cv2.circle(frame_annotated, (x, y), 8, (255, 255, 255), 1)

                    # Dibujar conexiones del esqueleto
                    connections = [
                        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
                        (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
                        (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32),
                    ]
                    for a, b in connections:
                        xa = int(landmarks[a, 0] * width)
                        ya = int(landmarks[a, 1] * height)
                        xb = int(landmarks[b, 0] * width)
                        yb = int(landmarks[b, 1] * height)
                        if landmarks[a, 3] > 0.5 and landmarks[b, 3] > 0.5:
                            cv2.line(frame_annotated, (xa, ya), (xb, yb), (0, 255, 0), 2)

                    # Contar visibles por grupo
                    n_visible = int(np.sum(landmarks[:, 3] > 0.5))
                    visible_by_group = {}
                    for g, indices in GROUPS.items():
                        vis_count = sum(1 for i in indices if landmarks[i, 3] > 0.5)
                        visible_by_group[g] = vis_count

                    # Panel de info
                    info_y = 25
                    cv2.putText(frame_annotated, f"Keypoints: {n_visible}/33",
                                (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    info_y += 25

                    for g, count in visible_by_group.items():
                        color = COLORS[g]
                        status = f"{g}: {count}/{len(GROUPS[g])}"
                        cv2.putText(frame_annotated, status,
                                    (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        info_y += 20

                    # Verificar si hay piernas visibles
                    legs_visible = visible_by_group["left_leg"] + visible_by_group["right_leg"]
                    if legs_visible < 4:
                        cv2.putText(frame_annotated, "ALEJATE – no se ven las piernas",
                                    (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    else:
                        cv2.putText(frame_annotated, "Cuerpo completo detectado",
                                    (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                else:
                    cv2.putText(frame_annotated, "Sin deteccion",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                cv2.imshow("Keypoints Sprint", frame_annotated)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            elif key == ord("s"):
                path = output_dir / f"keypoints_{frame_count:04d}.png"
                cv2.imwrite(str(path), frame_annotated)
                print(f"  Guardado: {path}")
            elif key == ord(" "):
                paused = not paused

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n  Frames procesados: {frame_count}")


if __name__ == "__main__":
    main()
