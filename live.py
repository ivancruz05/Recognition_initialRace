"""Captura en vivo unificada: keypoints, distancias o ángulos.

Uso:
    python live.py                 # cámara automática, modo keypoints
    python live.py --iphone        # forzar cámara del iPhone
    python live.py --camera N      # cámara específica
    python live.py --mode 2        # 1=keypoints 2=distancias 3=ángulos
    python live.py --headless 5    # guardar 5 frames anotados sin ventana
"""

import argparse

import cv2

from src import annotate, camera, landmarks as lm
from src.config import SAMPLES_DIR, VISIBILITY_THRESHOLD, ensure_dir
from src.measurements import REFERENCE_DISTANCES, estimate_all_distances, estimate_joint_angles
from src.pose import PoseDetector

MODES = {1: "Keypoints", 2: "Distancias", 3: "Angulos"}

CONTROLS_HINT = "q=salir s=guardar espacio=pausa 1-3=modo"


def render_frame(frame, detector, mode):
    """Detecta pose y anota el frame. Devuelve (frame_anotado, landmarks_o_None)."""
    results = detector.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    annotated = frame.copy()

    if not results:
        cv2.putText(annotated, "Sin deteccion", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return annotated, None

    landmarks = detector.get_landmarks_normalized(results)
    annotate.draw_skeleton(annotated, landmarks)
    annotate.draw_keypoints(annotated, landmarks)

    height, width = annotated.shape[:2]
    n_visible = int((landmarks[:, 3] > VISIBILITY_THRESHOLD).sum())
    lines = [(f"{MODES[mode]} | Keypoints: {n_visible}/33", (0, 255, 0))]

    if mode == 1:
        lines.extend(_keypoint_lines(landmarks))

    elif mode == 2:
        distances, reference = estimate_all_distances(landmarks, width, height)
        if distances:
            lines.append((f"Ref: {reference} ({REFERENCE_DISTANCES[reference]:.2f}m)", (200, 200, 200)))
            lines.extend((f"{name}: {dist:.3f}m", (0, 255, 0)) for name, dist in sorted(distances.items()))
        else:
            lines.append(("Alejate para ver el cuerpo completo", (0, 0, 255)))

    elif mode == 3:
        angles = estimate_joint_angles(landmarks)
        if angles:
            lines.extend((f"{name}: {angle:.1f} grados", (0, 200, 255)) for name, angle in sorted(angles.items()))
        else:
            lines.append(("Alejate para ver el cuerpo completo", (0, 0, 255)))

    annotate.draw_lines(annotated, lines)
    cv2.putText(annotated, CONTROLS_HINT, (10, height - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    return annotated, landmarks


def _keypoint_lines(landmarks):
    lines = []
    for name, idx in lm.KEY_POINTS:
        x, y, _, visibility = landmarks[idx]
        visible = visibility > VISIBILITY_THRESHOLD
        status = "OK" if visible else "NO"
        color = (0, 255, 0) if visible else (0, 0, 255)
        lines.append((f"{name}: ({x:.2f}, {y:.2f}) [{status}]", color))
    return lines


def run_gui(index, initial_mode=1):
    cap, used = camera.open_camera(index)
    if cap is None:
        print("Error: no se encontro camara disponible.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  Camara {used}: {width}x{height}")
    print("  Controles: q=salir  s=guardar  espacio=pausa  1-3=modo")

    samples_dir = ensure_dir(SAMPLES_DIR)
    mode, paused, frame_count, last_frame = initial_mode, False, 0, None

    with PoseDetector(model_complexity=1) as detector:
        while True:
            if not paused:
                ok, frame = cap.read()
                if not ok:
                    break

                frame_count += 1
                last_frame, _ = render_frame(frame, detector, mode)
                cv2.imshow("Sprint Analysis", last_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                if last_frame is not None:
                    path = samples_dir / f"live_{frame_count:04d}.png"
                    cv2.imwrite(str(path), last_frame)
                    print(f"  Guardado: {path}")
            elif key == ord(" "):
                paused = not paused
            elif ord("1") <= key <= ord("3"):
                mode = key - ord("0")

    cap.release()
    cv2.destroyAllWindows()
    print(f"  Frames procesados: {frame_count}")


def run_headless(index, n_frames, mode=1):
    """Captura N frames anotados y los guarda sin abrir ventana."""
    cap, _ = camera.open_camera(index)
    if cap is None:
        print("Error: no se encontro camara disponible.")
        return

    samples_dir = ensure_dir(SAMPLES_DIR)
    total = with_pose = 0

    with PoseDetector(model_complexity=1) as detector:
        for i in range(n_frames):
            ok, frame = cap.read()
            if not ok:
                break

            total += 1
            annotated, landmarks = render_frame(frame, detector, mode)
            if landmarks is not None:
                with_pose += 1

            path = samples_dir / f"live_{i:04d}.png"
            cv2.imwrite(str(path), annotated)
            print(f"  Frame {i}: {'pose detectada' if landmarks is not None else 'sin deteccion'} -> {path}")

    cap.release()
    success_rate = with_pose / max(total, 1) * 100
    print(f"  Resultado: {with_pose}/{total} frames con pose ({success_rate:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Captura en vivo unificada (FASE 1).")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--iphone", action="store_true", help="usar la camara del iPhone")
    source.add_argument("--camera", type=int, help="indice de camara")
    parser.add_argument("--mode", type=int, choices=sorted(MODES), default=1,
                        help="modo inicial: 1=keypoints 2=distancias 3=angulos")
    parser.add_argument("--headless", type=int, metavar="N",
                        help="guardar N frames anotados sin abrir ventana")
    args = parser.parse_args()

    if args.iphone:
        index = camera.find_iphone_camera()
        if index is None:
            print("  iPhone no detectado; usando FaceTime HD (camara 0).")
            index = 0
    elif args.camera is not None:
        index = args.camera
    else:
        index = None

    if args.headless:
        run_headless(index, args.headless, args.mode)
    else:
        run_gui(index, args.mode)


if __name__ == "__main__":
    main()