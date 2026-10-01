# Trazabilidad: Documento DRON ↔ Código

Este documento vincula cada requisito del **DOCUMENTO DRON** con el módulo de código que lo implementa. Sirve como insumo para completar el documento formal de la monografía.

## Requisitos generales

| Requisito del documento | Módulo(s) | Estado |
|---|---|---|
| Software de análisis de video | `detection/`, `training/`, `backend/` | ✅ |
| Dron autónomo DJI Spark | CLI `drone analyze` acepta video `.mp4` de cualquier fuente | ✅ |
| Carrera de 10 m con salida de tacos | Configuración por defecto de calibración ArUco (10 m) | ✅ |
| 20 estudiantes grupo piloto | `data/pilot/` (pendiente captura) | ⏳ |

## Variables biomecánicas

| Variable | Definición en código | Archivo principal |
|---|---|---|
| Postura | Score de calidad + ángulo de tronco | `detection/metrics/biomechanics.py` |
| Velocidad | Velocidad instantánea, máxima y media del centro de cadera | `detection/metrics/kinematics.py` |
| Longitud de zancada | Distancia entre contactos de pie consecutivos | `detection/metrics/kinematics.py` |
| Cadencia | Pasos por segundo a partir de eventos de contacto | `detection/metrics/kinematics.py` |

## Pipeline del documento (sección 3.3.1)

| Etapa del pipeline | Implementación | Archivo(s) |
|---|---|---|
| Estabilización del video | `VideoStabilizer` (optical flow + homografía) | `detection/vision/stabilizer.py` |
| Detección y seguimiento del atleta | `AthleteTracker` (YOLOv8 + ByteTrack) | `detection/vision/tracker.py` |
| Transformación px→m con marcadores | `ArUcoCalibration` + `default_track_marker_config` | `detection/vision/calibration.py` |
| Estimación de pose | `PoseDetector` (MediaPipe) con `detect_in_roi` | `detection/vision/pose.py` |
| Cálculo de variables cinemáticas | `KinematicsAnalyzer` | `detection/metrics/kinematics.py` |

## Validación (secciones 3.3.2, 3.3.3, 3.5)

| Requisito | Implementación | Archivo(s) |
|---|---|---|
| Registro manual de referencia cuadro a cuadro | Plantilla JSON generada por CLI | `detection/cli.py` |
| Comparación automática vs. manual | `ValidationAnalyzer` | `detection/metrics/validation.py` |
| Error absoluto y porcentual | Cálculo por variable + MAPE | `detection/metrics/validation.py` |
| Criterios ISO/IEC 25010 | Bandas EXCELLENT / ACCEPTABLE / LIMIT / UNACCEPTABLE | `detection/metrics/validation.py` |

## Interfaz de usuario

| Comando | Propósito | Archivo |
|---|---|---|
| `drone calibrate` | Generar calibración px→m | `detection/cli.py` |
| `drone analyze` | Ejecutar el pipeline completo | `detection/cli.py` |
| `drone annotate` | Generar video anotado | `detection/cli.py` |
| `drone groundtruth` | Crear plantilla de anotación manual | `detection/cli.py` |
| `drone validate` | Comparar resultados vs. ground truth | `detection/cli.py` |

## Tests

| Componente probado | Archivo de test |
|---|---|
| Calibración ArUco | `tests/detection/test_calibration.py` |
| Tracking / crop | `tests/detection/test_tracker.py` |
| Cinemática | `tests/detection/test_kinematics.py` |
| Validación | `tests/detection/test_validation.py` |
| Estabilización | `tests/detection/test_stabilizer.py` |
| Geometría de landmarks | `tests/test_measurements.py` |

## Elementos pendientes en el documento formal

Las siguientes secciones del `.docx` aún contienen texto de plantilla y deben ser completados por las autoras:

- Sección **3.4** (falta en el cuerpo del documento).
- **Tabla 3.4** técnicas e instrumentos (celdas vacías).
- **1.5.2 Preguntas específicas** (aparece en TOC pero no en cuerpo).
- **Conclusiones**, **Recomendaciones**, **Figuras**, **Tablas**, **Apéndices**.

## Notas para las autoras

1. El **DOCUMENTO DRON** es la fuente de verdad del proyecto.
2. El código refleja exactamente el alcance del documento: 4 variables, dron, 10 m, validación con 20 estudiantes.
3. Los videos de dron aún no están disponibles en el repositorio; cuando lleguen deben copiarse a `data/drone/<sesion>/`.
4. Para la validación de campo se debe usar `drone groundtruth` para generar la plantilla, completarla manualmente y luego `drone validate`.
