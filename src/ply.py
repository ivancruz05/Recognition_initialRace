"""Guardado de point clouds en formato PLY."""

from pathlib import Path


def save_ply(path, points, colors):
    """Guarda una point cloud en PLY ASCII.

    Args:
        path: ruta de salida (.ply).
        points: ndarray (N, 3) con coordenadas en metros.
        colors: ndarray (N, 3) con colores RGB normalizados (0-1).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

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
            x, y, z = points[i]
            r, g, b = (int(channel * 255) for channel in colors[i][:3])
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {r} {g} {b}\n")

    return path