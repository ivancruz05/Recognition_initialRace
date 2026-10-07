# Trazabilidad del reconocimiento local

Este documento relaciona el flujo vigente de captura/análisis con su implementación.
El MVP usa una cámara lateral de iPhone conectada al Mac mediante Continuity Camera
o un archivo MP4/MOV. Se procesa un atleta por sesión con un código manual; no se
identifica automáticamente a la persona.

## Flujo y módulos

| Etapa | Implementación |
|---|---|
| Vista previa, overlay y gate de pose lista | `detection/infrastructure/camera_source.py`, `detection/domain/entities.py` |
| Captura manual y video original MP4 | `detection/infrastructure/camera_source.py`, `detection/infrastructure/raw_video_writer.py` |
| Lectura alternativa de video | `detection/infrastructure/video_file_source.py` |
| Orquestación de una sesión | `detection/application/process_session.py` |
| Detección de pose | `detection/infrastructure/mediapipe_pose_detector.py` |
| Análisis de ángulos por frame | `detection/infrastructure/mediapipe_analyzer.py`, `detection/domain/angle_calculation.py` |
| Escritura incremental de ángulos + landmarks/confianza | `detection/infrastructure/csv_result_writer.py` |
| Estado y conteos de archivos CSV/MP4 | `detection/infrastructure/session_manifest_writer.py` |
| Comandos de usuario | `detection/local_cli.py`, `detection/__main__.py` |

## Entrada, proceso y salida

En captura en vivo se muestra una vista previa con puntos y conexiones. `t` solo
inicia tras cinco frames consecutivos con suficientes ángulos de miembro
inferior; `s` finaliza y `q` detiene. La preparación no certifica la vista lateral.
El ID del atleta es manual y la sesión se genera si se omite. En vivo se conserva
un MP4 BGR sin anotaciones, desde el instante de inicio, junto al CSV y un
manifiesto JSON de estado. Los archivos existentes no se sobrescriben. También
se puede analizar un MP4/MOV ya grabado, que produce CSV y manifiesto mientras el
original se conserva.

Los resultados incluyen índices y tiempos de frame, detección/listura de pose,
visibilidad y coordenadas x/y normalizadas de landmarks, además de ángulos
disponibles de rodillas, caderas, tobillos y tronco. Valores no disponibles quedan
vacíos. No hay coordenadas métricas ni etiquetas humanas para entrenamiento aún.
`frame_index` es la clave de unión CSV↔MP4; la duración del MP4 a tasa constante
solo aproxima los timestamps monotónicos del CSV. El manifiesto `complete` solo se
marca tras cerrar las salidas y, cuando se genera MP4, reabrirlo y decodificarlo;
el conteo decodificado debe coincidir con las escrituras de frames aceptadas.
`empty` representa cualquier sesión cerrada correctamente sin frames, tanto una
captura cancelada antes de `t` como un archivo sin frames. `failed` puede conservar
salidas parciales. Si una caída o interrupción deja `in_progress` persistente, el
intento es incompleto y no debe usarse hasta revisión. El usuario debe revisar los
manifiestos antes de incorporar intentos al dataset.

## Límites del MVP

La medición es angular y bidimensional. No incluye calibración métrica, velocidad,
distancia, longitud de zancada ni cadencia. Tampoco incluye app móvil, Django,
dron, LiDAR, YOLO, estabilización, ArUco ni modelos o métricas ML legacy.

## Pruebas

La cobertura actual está en `tests/detection/test_recognition_domain.py`,
`test_recognition_application.py`, `test_recognition_infrastructure.py`,
`test_local_cli.py` y `test_layering.py`. Ejecución desde la raíz:

```bash
.venv/bin/python -m pytest -q
```
