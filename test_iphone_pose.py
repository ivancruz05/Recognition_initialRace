"""
Test de pose con la cámara del iPhone (índice 1).
Muestra keypoints en tiempo real.
"""

import cv2
import mediapipe as mp
import time

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

CAMERA_INDEX = 1  # iPhone

def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara del iPhone")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Cámara iPhone activa: {w}x{h}")
    print("Posiciónate frente a la cámara (vista lateral, cuerpo completo)")
    print("Presiona 'q' para salir\n")

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        frame_count = 0
        start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)

            n_landmarks = 0
            if results.pose_landmarks:
                n_landmarks = len(results.pose_landmarks.landmark)
                mp_drawing.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1)
                )

            frame_count += 1
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0

            cv2.putText(frame, f"Keypoints: {n_landmarks}/33 | FPS: {fps:.1f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "q=salir | s=guardar frame",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("iPhone Pose Test", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                cv2.imwrite("data/samples/iphone_pose_test.png", frame)
                print("Frame guardado: data/samples/iphone_pose_test.png")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal frames: {frame_count}, FPS promedio: {frame_count/elapsed:.1f}")

if __name__ == "__main__":
    main()
