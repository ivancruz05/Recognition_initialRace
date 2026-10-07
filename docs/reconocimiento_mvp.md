# Reconocimiento biomecánico: MVP de captura local

## Alcance actual

- Capturar desde una cámara que macOS expone a OpenCV; el iPhone por Continuity
  Camera ya fue comprobado como fuente en este entorno.
- Procesar una sola persona por sesión desde una vista lateral fija.
- Aceptar también videos `.mp4` y `.mov` para análisis posterior.
- Mostrar pose/esqueleto durante la vista previa y habilitar el inicio tras cinco
  frames consecutivos con suficientes ángulos de miembro inferior.
- Guardar el video original de cada captura en vivo como MP4 y escribir al CSV
  landmarks normalizados, visibilidad y ángulos por frame.
- No incluye app móvil, Django, reconocimiento de identidad, YOLO/tracking, dron,
  LiDAR, estabilización, ArUco, modelos ML legacy, velocidad/cadencia ni
  distancias calibradas.

La cámara presenta el esqueleto detectado. `t` solo inicia después de cinco
frames consecutivos con pose lista; `s` termina y `q` detiene. La condición de
“lista” verifica que haya ángulos de cadera, rodilla y tobillo calculables en un
lado; **no confirma que la cámara esté realmente de lado**. El video MP4 empieza
en `t` y conserva frames BGR sin el dibujo superpuesto. Los frames de vista
previa no se guardan. Solo se procesa una pose; `athlete_id` es un código manual,
no una identificación automática.

## Preparar el entorno

Desde la raíz del repositorio:

```bash
python3.9 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

En macOS, concede permiso de cámara a la aplicación/terminal que ejecuta Python.
Conecta el iPhone, selecciona Continuity Camera y verifica el índice que OpenCV
puede abrir.

## Capturar desde la cámara

```bash
.venv/bin/python -m detection capture \
  --camera-index 0 \
  --athlete-id atleta-001 \
  --session-id sesion-001 \
  --output resultados/sesion-001.csv
```

Por defecto se crea también `resultados/sesion-001.mp4`. Se puede indicar otra
ruta con `--video-output`. Enfoca la ventana, corrige la posición hasta ver el
esqueleto y el estado `READY`, y pulsa `t`; `s` finaliza. `--camera-index` es
explícito: no se escanean índices automáticamente. Cambia `0` por el índice
comprobado en tu Mac. Si los archivos de salida ya existen, el comando se niega
a sobrescribirlos: usa nombres únicos por intento.

## Analizar un archivo de teléfono

```bash
.venv/bin/python -m detection analyze-video ./intento.mov \
  --athlete-id atleta-001 \
  --output resultados/intento.csv
```

La fuente de cámara y la fuente de archivo usan el mismo analizador y el mismo
formato CSV.

## Datos por frame

El CSV incluye `capture_source`, `source_reference`, `camera_index`, la vista y
altura de cámara declaradas, `session_id`, `athlete_id`, `frame_index`,
`timestamp_seconds`, `pose_detected`, `pose_ready`, `any_angle_valid`, ángulos de
rodillas, caderas, tobillos y tronco, y `x`, `y`, `visibility` normalizados para
cada landmark anatómico que entrega el detector. Puntos/ángulos ausentes quedan
como celdas vacías; no se reemplazan por cero. Se conserva una fila por cada
frame capturado, incluso si la pose no está lista, para auditar la calidad.

Cada captura en vivo produce CSV, MP4 raw y un manifiesto JSON con el mismo nombre
base. El análisis de un archivo mantiene el original y produce CSV + manifiesto.
El manifiesto registra estado, IDs, configuración declarada, referencias de
archivos y conteos. `complete` indica que la sesión terminó correctamente y sus
salidas se cerraron; cuando la sesión produce un MP4, este se reabre y decodifica,
y el número de frames decodificados debe coincidir con las escrituras aceptadas.
`empty` indica cualquier sesión cerrada correctamente sin frames: por ejemplo,
una captura cancelada antes de `t` o un archivo de video sin frames. `failed` puede
retener salidas parciales y requiere revisión. Si una caída o interrupción deja el
manifiesto persistente en `in_progress`, trata el intento como incompleto y no lo
uses hasta revisarlo. Antes de incorporar cualquier intento al dataset, revisa su
manifiesto y los artefactos asociados; no asumas que un archivo presente es válido.

`frame_index` es la clave para unir cada fila CSV con el frame correspondiente
del MP4. El CSV conserva el tiempo monotónico observado y el MP4 usa una tasa
constante estimada desde el preview; por ello la duración reproducida del MP4 es
aproximada y puede diferir ligeramente del timestamp CSV. **El CSV contiene
coordenadas 2D normalizadas, no posiciones 3D ni coordenadas en metros**. Aún no
se registran etiquetas expertas para entrenamiento: deben definirse y anotarse
por intento/fase antes de usar estos datos para un modelo.

Mantén el protocolo físico constante: lente principal sin zoom digital, teléfono
estable en orientación horizontal, cámara aproximadamente a 1 m, vista lateral,
cuerpo completo en cuadro, buena iluminación y un solo atleta. La altura/vista
son condiciones del protocolo, no se verifican automáticamente ni constituyen
calibración métrica. No interpretes estos datos como velocidad o distancia en
unidades reales.

## Antes de grabar participantes

El MP4 conserva imágenes originales y el CSV contiene observaciones biomecánicas;
ambos son datos sensibles. Antes de recopilar datos de otras personas, define y
obtén el consentimiento informado, usa códigos en lugar de nombres, limita el
acceso a los archivos y acuerda dónde se almacenarán, durante cuánto tiempo y
cómo se borrarán. La aplicación local no aplica permisos ni retención automática.

La metodología vigente y el mapeo de implementación están documentados en
[`metodologia_avance.md`](metodologia_avance.md) y
[`trazabilidad.md`](trazabilidad.md).
