"""
Selector de cámara - permite elegir entre FaceTime e iPhone.
Muestra preview en tiempo real para verificar cuál ve el cuerpo.
"""

import cv2
import sys


def main():
    print("=" * 60)
    print("  Selector de Cámara")
    print("=" * 60)
    print("\n  Cámaras disponibles:")

    cameras = []
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append((i, w, h))
            cap.release()

    if not cameras:
        print("  No se encontraron cámaras.")
        return

    for idx, w, h in cameras:
        name = "FaceTime HD" if idx == 0 else f"iPhone ({idx})"
        print(f"    [{idx}] {name} - {w}x{h}")

    print(f"\n  Selecciona una cámara (0-{len(cameras)-1}): ", end="")

    try:
        choice = int(input())
    except ValueError:
        choice = 0

    if choice not in [c[0] for c in cameras]:
        print(f"  Opción inválida, usando cámara 0")
        choice = 0

    cap = cv2.VideoCapture(choice)
    if not cap.isOpened():
        print("  Error: No se pudo abrir la cámara.")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"\n  Cámara {choice} activa: {w}x{h}")
    print("  Presiona 'q' para salir, '1-4' para cambiar cámara\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Info en pantalla
        cv2.putText(frame, f"Camara {choice} | q=salir | 1-4=cambiar",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"{w}x{h}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Camera Selector", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key in [ord(str(i)) for i in range(5)]:
            new_idx = int(chr(key))
            if new_idx != choice:
                cap.release()
                cap = cv2.VideoCapture(new_idx)
                if cap.isOpened():
                    choice = new_idx
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"  Cambiado a cámara {choice}: {w}x{h}")
                else:
                    print(f"  Cámara {new_idx} no disponible")
                    cap = cv2.VideoCapture(choice)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
