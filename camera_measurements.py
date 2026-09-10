"""
Estimacion de distancias con camara 2D usando referencia conocida.
Si conocemos un tamaño real del cuerpo, podemos estimar escalas para otras medidas.
"""

import cv2
import numpy as np
from cv.pose_detector import PoseDetector


# Distancias de referencia conocidas del cuerpo humano (en metros)
# Estos valores son promedios y pueden variar por persona
REFERENCE_DISTANCES = {
    "shoulder_width": 0.40,   # Ancho de hombros promedio
    "hip_width": 0.35,        # Ancho de caderas promedio
    "upper_arm": 0.30,        # Longitud brazo superior
    "forearm": 0.25,          # Longitud antebrazo
    "thigh": 0.45,            # Longitud muslo
    "shank": 0.40,            # Longitud pantorrilla
    "torso_length": 0.50,     # Longitud del torso
}

# Conexiones para estimar distancias
DISTANCE_PAIRS = {
    "shoulder_width": (11, 12),
    "hip_width": (23, 24),
    "left_thigh": (23, 25),
    "right_thigh": (24, 26),
    "left_shank": (25, 27),
    "right_shank": (26, 28),
    "left_upper_arm": (11, 13),
    "right_upper_arm": (12, 14),
    "left_forearm": (13, 15),
    "right_forearm": (14, 16),
    "torso": (11, 23),
}


def calculate_pixel_distance(landmarks, idx_a, idx_b, width, height):
    """Calcula distancia en pixeles entre dos landmarks."""
    xa = landmarks[idx_a, 0] * width
    ya = landmarks[idx_a, 1] * height
    xb = landmarks[idx_b, 0] * width
    yb = landmarks[idx_b, 1] * height
    return np.sqrt((xa - xb) ** 2 + (ya - yb) ** 2)


def estimate_scale_from_reference(landmarks, width, height, reference_name="shoulder_width"):
    """Estima la escala (metros/pixel) usando una referencia conocida.

    Args:
        landmarks: ndarray (33, 4) con [x, y, z, visibility] normalizados.
        width, height: dimensiones del frame.
        reference_name: nombre de la referencia a usar para calibrar.

    Returns:
        float: metros por pixel, o None si la referencia no es visible.
    """
    if reference_name not in DISTANCE_PAIRS:
        return None

    idx_a, idx_b = DISTANCE_PAIRS[reference_name]

    # Verificar que ambos landmarks sean visibles
    if landmarks[idx_a, 3] < 0.5 or landmarks[idx_b, 3] < 0.5:
        return None

    pixel_dist = calculate_pixel_distance(landmarks, idx_a, idx_b, width, height)
    real_dist = REFERENCE_DISTANCES[reference_name]

    if pixel_dist < 1e-6:
        return None

    # Retornar metros por pixel
    return real_dist / pixel_dist


def estimate_all_distances(landmarks, width, height):
    """Estima todas las distancias del cuerpo usando la mejor referencia disponible.

    Returns:
        dict con nombre -> valor en metros.
    """
    # Intentar calibrar con diferentes referencias (en orden de prioridad)
    scale = None
    used_reference = None

    for ref_name in ["shoulder_width", "hip_width", "torso"]:
        scale = estimate_scale_from_reference(landmarks, width, height, ref_name)
        if scale is not None:
            used_reference = ref_name
            break

    if scale is None:
        return None, None

    # Calcular todas las distancias usando la escala estimada
    distances = {}
    for name, (idx_a, idx_b) in DISTANCE_PAIRS.items():
        if landmarks[idx_a, 3] > 0.5 and landmarks[idx_b, 3] > 0.5:
            pixel_dist = calculate_pixel_distance(landmarks, idx_a, idx_b, width, height)
            distances[name] = pixel_dist * scale

    return distances, used_reference


def calculate_angle(point_a, point_b, point_c):
    """Calcula el angulo en el punto_b formado por a-b-c.

    Args:
        point_a, point_b, point_c: arrays con coordenadas (x, y).

    Returns:
        float: angulo en grados.
    """
    a = np.array(point_a)
    b = np.array(point_b)
    c = np.array(point_c)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

    return angle


def estimate_joint_angles(landmarks):
    """Estima angulos articulares clave para sprint.

    Returns:
        dict con nombre_angulo -> valor en grados.
    """
    angles = {}

    # Angulo de rodilla izquierda (cadera-rodilla-tobillo)
    if all(landmarks[i, 3] > 0.5 for i in [23, 25, 27]):
        hip = landmarks[23, :2]
        knee = landmarks[25, :2]
        ankle = landmarks[27, :2]
        angles["left_knee"] = calculate_angle(hip, knee, ankle)

    # Angulo de rodilla derecha
    if all(landmarks[i, 3] > 0.5 for i in [24, 26, 28]):
        hip = landmarks[24, :2]
        knee = landmarks[26, :2]
        ankle = landmarks[28, :2]
        angles["right_knee"] = calculate_angle(hip, knee, ankle)

    # Angulo de cadera izquierda (hombro-cadera-rodilla)
    if all(landmarks[i, 3] > 0.5 for i in [11, 23, 25]):
        shoulder = landmarks[11, :2]
        hip = landmarks[23, :2]
        knee = landmarks[25, :2]
        angles["left_hip"] = calculate_angle(shoulder, hip, knee)

    # Angulo de cadera derecha
    if all(landmarks[i, 3] > 0.5 for i in [12, 24, 26]):
        shoulder = landmarks[12, :2]
        hip = landmarks[24, :2]
        knee = landmarks[26, :2]
        angles["right_hip"] = calculate_angle(shoulder, hip, knee)

    # Angulo de codo izquierdo (hombro-codo-muneca)
    if all(landmarks[i, 3] > 0.5 for i in [11, 13, 15]):
        shoulder = landmarks[11, :2]
        elbow = landmarks[13, :2]
        wrist = landmarks[15, :2]
        angles["left_elbow"] = calculate_angle(shoulder, elbow, wrist)

    # Angulo de codo derecho
    if all(landmarks[i, 3] > 0.5 for i in [12, 14, 16]):
        shoulder = landmarks[12, :2]
        elbow = landmarks[14, :2]
        wrist = landmarks[16, :2]
        angles["right_elbow"] = calculate_angle(shoulder, elbow, wrist)

    # Inclinacion del torso (angulo del torso con la vertical)
    if all(landmarks[i, 3] > 0.5 for i in [11, 12, 23, 24]):
        mid_shoulder = (landmarks[11, :2] + landmarks[12, :2]) / 2
        mid_hip = (landmarks[23, :2] + landmarks[24, :2]) / 2
        # Angulo con la vertical
        dx = mid_shoulder[0] - mid_hip[0]
        dy = mid_shoulder[1] - mid_hip[1]
        angles["torso_inclination"] = np.degrees(np.arctan2(abs(dx), abs(dy)))

    return angles


def run_camera_with_measurements():
    """Ejecuta la camara con estimacion de distancias y angulos."""
    print("=" * 60)
    print("  Camara 2D + Estimacion de Distancias y Angulos")
    print("=" * 60)
    print("\n  Usando referencia: ancho de hombros (~40cm)")
    print("  Para mejor precision, alejate para ver cuerpo completo.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la camara.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    with PoseDetector(model_complexity=1) as detector:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = detector.detect(rgb)
            frame_annotated = frame.copy()

            if results:
                landmarks = detector.get_landmarks_normalized(results)

                # Dibujar landmarks
                for idx in range(33):
                    x = int(landmarks[idx, 0] * width)
                    y = int(landmarks[idx, 1] * height)
                    vis = landmarks[idx, 3]
                    color = (0, 255, 0) if vis > 0.5 else (0, 0, 255)
                    cv2.circle(frame_annotated, (x, y), 4, color, -1)

                # Estimar distancias
                distances, ref_used = estimate_all_distances(landmarks, width, height)

                # Estimar angulos
                angles = estimate_joint_angles(landmarks)

                # Panel de info
                y_pos = 25
                cv2.putText(frame_annotated, "DISTANCIAS (estimadas)",
                            (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                y_pos += 25

                if distances:
                    cv2.putText(frame_annotated, f"Ref: {ref_used} ({REFERENCE_DISTANCES[ref_used]:.2f}m)",
                                (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                    y_pos += 20

                    for name, dist in sorted(distances.items()):
                        text = f"{name}: {dist:.3f}m"
                        cv2.putText(frame_annotated, text,
                                    (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                        y_pos += 18
                else:
                    cv2.putText(frame_annotated, "No se pudo calibrar",
                                (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                    y_pos += 20

                # Angulos
                y_pos += 10
                cv2.putText(frame_annotated, "ANGULOS",
                            (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                y_pos += 25

                for name, angle in sorted(angles.items()):
                    text = f"{name}: {angle:.1f} grados"
                    cv2.putText(frame_annotated, text,
                                (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
                    y_pos += 18

            cv2.imshow("Mediciones 2D", frame_annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_camera_with_measurements()
