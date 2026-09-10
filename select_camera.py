"""Selector de camara con preview en vivo.

Uso:
    python select_camera.py
"""

import cv2

from src import camera


def main():
    print("=" * 60)
    print("  Selector de Camera")
    print("=" * 60)

    cameras = camera.list_cameras()
    if not cameras:
        print("  No se encontraron camaras.")
        return

    print("\n  Camaras disponibles:")
    for index, width, height in cameras:
        name = "FaceTime HD" if index == 0 else f"Camera {index}"
        print(f"    [{index}] {name} - {width}x{height}")

    choice = _ask_choice([i for i, _, _ in cameras])

    cap, used = camera.open_camera(choice)
    if cap is None:
        print(f"  Error: no se pudo abrir la camara {choice}.")
        return

    print(f"\n  Camera {used} activa. Presiona 'q' para salir.\n")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("Camera Selector", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def _ask_choice(options):
    print(f"\n  Selecciona una camara {options}: ", end="")
    try:
        choice = int(input())
    except ValueError:
        return options[0]
    return choice if choice in options else options[0]


if __name__ == "__main__":
    main()