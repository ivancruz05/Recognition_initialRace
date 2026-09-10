import cv2
import numpy as np
from pathlib import Path


# Posiciones de un atleta en posicion de arranque (normalizadas 0-1)
# Simula vista lateral de un atleta en bloques de salida
STARTING_POSITION_LANDMARKS = {
    "nose": (0.35, 0.22),
    "left_shoulder": (0.33, 0.32),
    "right_shoulder": (0.37, 0.33),
    "left_elbow": (0.28, 0.40),
    "right_elbow": (0.32, 0.42),
    "left_wrist": (0.24, 0.48),
    "right_wrist": (0.28, 0.50),
    "left_hip": (0.38, 0.50),
    "right_hip": (0.42, 0.51),
    "left_knee": (0.48, 0.62),
    "right_knee": (0.54, 0.65),
    "left_ankle": (0.42, 0.78),
    "right_ankle": (0.58, 0.80),
    "left_heel": (0.40, 0.80),
    "right_heel": (0.56, 0.82),
    "left_foot_index": (0.36, 0.82),
    "right_foot_index": (0.62, 0.82),
}


def generate_skeleton_image(width=640, height=480, scale=1.0, offset_x=0.0, offset_y=0.0):
    """Genera una imagen sintetica con un skeleton de atleta en posicion de arranque.

    Args:
        width, height: dimensiones de la imagen.
        scale: escala del skeleton (1.0 = normal).
        offset_x, offset_y: desplazamiento del skeleton (0-1).

    Returns:
        ndarray BGR con el skeleton dibujado.
    """
    img = np.ones((height, width, 3), dtype=np.uint8) * 240

    # Dibujar linea de salida
    line_x = int(0.2 * width)
    cv2.line(img, (line_x, 0), (line_x, height), (0, 0, 200), 2)

    # Conexiones del esqueleto
    connections = [
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("right_shoulder", "right_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_elbow", "right_wrist"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_hip", "left_knee"),
        ("right_hip", "right_knee"),
        ("left_knee", "left_ankle"),
        ("right_knee", "right_ankle"),
        ("left_ankle", "left_heel"),
        ("right_ankle", "right_heel"),
        ("left_heel", "left_foot_index"),
        ("right_heel", "right_foot_index"),
    ]

    def to_px(name):
        x, y = STARTING_POSITION_LANDMARKS[name]
        x = (x + offset_x) * scale * width
        y = (y + offset_y) * scale * height
        return int(x), int(y)

    # Dibujar conexiones (huesos)
    for a, b in connections:
        pt_a = to_px(a)
        pt_b = to_px(b)
        cv2.line(img, pt_a, pt_b, (80, 80, 80), 2)

    # Dibujar articulaciones
    for name, (x, y) in STARTING_POSITION_LANDMARKS.items():
        px = to_px(name)
        color = (0, 120, 255) if "left" in name else (255, 120, 0)
        cv2.circle(img, px, 5, color, -1)

    # Texto informativo
    cv2.putText(img, "Synthetic Sprint Start", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

    return img


def generate_depth_map(width=256, height=192, base_depth=2.0, noise_level=0.02):
    """Genera un depth map sintetico simulando LiDAR.

    Simula un atleta a ~2 metros de distancia con profundidad variable
    por cada parte del cuerpo.

    Args:
        width, height: dimensiones del depth map.
        base_depth: profundidad base en metros.
        noise_level: nivel de ruido en metros.

    Returns:
        ndarray (H, W) float32 con profundidad en metros.
    """
    depth = np.full((height, width), base_depth, dtype=np.float32)

    # Simular silueta del atleta con profundidades variables
    # Cabeza (mas cercana)
    _draw_depth_blob(depth, 0.35, 0.22, 0.06, base_depth - 0.15, width, height)
    # Hombros
    _draw_depth_blob(depth, 0.33, 0.32, 0.05, base_depth - 0.10, width, height)
    _draw_depth_blob(depth, 0.37, 0.33, 0.05, base_depth - 0.08, width, height)
    # Codos
    _draw_depth_blob(depth, 0.28, 0.40, 0.04, base_depth - 0.05, width, height)
    _draw_depth_blob(depth, 0.32, 0.42, 0.04, base_depth - 0.03, width, height)
    # Muñecas
    _draw_depth_blob(depth, 0.24, 0.48, 0.03, base_depth + 0.02, width, height)
    _draw_depth_blob(depth, 0.28, 0.50, 0.03, base_depth + 0.05, width, height)
    # Caderas
    _draw_depth_blob(depth, 0.38, 0.50, 0.06, base_depth + 0.05, width, height)
    _draw_depth_blob(depth, 0.42, 0.51, 0.06, base_depth + 0.08, width, height)
    # Rodillas
    _draw_depth_blob(depth, 0.48, 0.62, 0.05, base_depth + 0.15, width, height)
    _draw_depth_blob(depth, 0.54, 0.65, 0.05, base_depth + 0.18, width, height)
    # Tobillos
    _draw_depth_blob(depth, 0.42, 0.78, 0.04, base_depth + 0.10, width, height)
    _draw_depth_blob(depth, 0.58, 0.80, 0.04, base_depth + 0.12, width, height)
    # Pies
    _draw_depth_blob(depth, 0.36, 0.82, 0.04, base_depth + 0.08, width, height)
    _draw_depth_blob(depth, 0.62, 0.82, 0.04, base_depth + 0.10, width, height)

    # Agregar ruido realista
    noise = np.random.normal(0, noise_level, depth.shape).astype(np.float32)
    depth += noise

    # Asegurar que el fondo sea consistente
    mask = depth == base_depth
    depth[mask] = base_depth + np.random.normal(0, noise_level * 0.3, mask.sum()).astype(np.float32)

    return depth


def _draw_depth_blob(depth, cx_norm, cy_norm, radius_norm, value, img_w, img_h):
    """Dibuja un blob circular en el depth map."""
    h, w = depth.shape
    cx = int(cx_norm * w)
    cy = int(cy_norm * h)
    r = int(max(radius_norm * w, radius_norm * h))

    y_min = max(0, cy - r)
    y_max = min(h, cy + r + 1)
    x_min = max(0, cx - r)
    x_max = min(w, cx + r + 1)

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < r:
                factor = 1.0 - (dist / r) ** 2
                depth[y, x] = depth[y, x] * (1 - factor) + value * factor


def generate_synthetic_frame(width=640, height=480, depth_width=256, depth_height=192):
    """Genera un par (RGB frame, depth map) sintetico.

    Args:
        width, height: dimensiones del frame RGB.
        depth_width, depth_height: dimensiones del depth map.

    Returns:
        tuple: (rgb_frame_bgr, depth_map)
    """
    rgb = generate_skeleton_image(width, height)
    depth = generate_depth_map(depth_width, depth_height)
    return rgb, depth


def generate_synthetic_video(output_path, n_frames=30, fps=30, width=640, height=480):
    """Genera un video sintetico conframes de posicion de arranque.

    Args:
        output_path: ruta del archivo de salida (.mp4).
        n_frames: numero de frames.
        fps: frames por segundo.
        width, height: dimensiones del video.
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for i in range(n_frames):
        # Agregar ligera variacion frame a frame
        offset_x = np.random.uniform(-0.01, 0.01)
        offset_y = np.random.uniform(-0.01, 0.01)
        frame = generate_skeleton_image(width, height, offset_x=offset_x, offset_y=offset_y)
        writer.write(frame)

    writer.release()
    return output_path


def save_depth_map(depth_map, output_path):
    """Guarda un depth map como archivo numpy."""
    np.save(str(output_path), depth_map)
    return output_path
