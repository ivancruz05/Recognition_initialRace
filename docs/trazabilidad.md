# Trazabilidad: Documento DRON ↔ Código

Este documento vincula cada requisito del **DOCUMENTO DRON** con el módulo de código que lo implementa. Sirve como insumo para completar el documento formal de la monografía.

## Requisitos generales

| Requisito del documento | Módulo(s) | Estado |
|---|---|---|
| Software de análisis de video | `drone_analysis/` (paquete completo) | ✅ |
| Dron autónomo DJI Spark | CLI `drone analyze` acepta video `.mp4` de cualquier fuente | ✅ |
| Carrera de 10 m con salida de tacos | Configuración por defecto de calibración ArUco (10 m) | ✅ |
| 20 estudiantes grupo piloto | `data/pilot/` (pendiente captura) | ⏳ |

## Variables biomecánicas

| Variable | Definición en código | Archivo principal |
|---|---|---|
| Postura | Score de calidad + ángulo de tronco | `drone_analysis/analysis/biomechanics.py` |
| Velocidad | Velocidad instantánea, máxima y media del centro de cadera | `drone_analysis/analysis/kinematics.py` |
| Longitud de zancada | Distancia entre contactos de pie consecutivos | `drone_analysis/analysis/kinematics.py` |
| Cadencia | Pasos por segundo a partir de eventos de contacto | `drone_analysis/analysis/kinematics.py` |

## Pipeline del documento (sección 3.3.1)

| Etapa del pipeline | Implementación | Archivo(s) |
|---|---|---|
| Estabilización del video | `VideoStabilizer` (optical flow + homografía) | `drone_analysis/infrastructure/video/stabilizer.py` |
| Detección y seguimiento del atleta | `AthleteTracker` (YOLOv8 + ByteTrack) | `drone_analysis/infrastructure/tracking/athlete_tracker.py` |
| Transformación px→m con marcadores | `ArUcoCalibration` + `default_track_marker_config` | `drone_analysis/infrastructure/calibration/aruco.py` |
| Estimación de pose | `PoseDetector` (MediaPipe) con `detect_in_roi` | `drone_analysis/infrastructure/pose/detector.py` |
| Cálculo de variables cinemáticas | `KinematicsAnalyzer` | `drone_analysis/analysis/kinematics.py` |

## Validación (secciones 3.3.2, 3.3.3, 3.5)

| Requisito | Implementación | Archivo(s) |
|---|---|---|
| Registro manual de referencia cuadro a cuadro | Plantilla JSON generada por CLI | `drone_analysis/cli/commands/groundtruth.py` |
| Comparación automática vs. manual | `ValidationAnalyzer` | `drone_analysis/analysis/validation.py` |
| Error absoluto y porcentual | Cálculo por variable + MAPE | `drone_analysis/analysis/validation.py` |
| Criterios ISO/IEC 25010 | Bandas EXCELLENT / ACCEPTABLE / LIMIT / UNACCEPTABLE | `drone_analysis/analysis/validation.py` |

## Interfaz de usuario

| Comando | Propósito | Archivo |
|---|---|---|
| `drone calibrate` | Generar calibración px→m | `drone_analysis/cli/commands/calibrate.py` |
| `drone analyze` | Ejecutar el pipeline completo | `drone_analysis/cli/commands/analyze.py` |
| `drone annotate` | Generar video anotado | `drone_analysis/cli/commands/annotate.py` |
| `drone groundtruth` | Crear plantilla de anotación manual | `drone_analysis/cli/commands/groundtruth.py` |
| `drone validate` | Comparar resultados vs. ground truth | `drone_analysis/cli/commands/validate.py` |

## Tests

| Componente probado | Archivo de test |
|---|---|
| Calibración ArUco | `tests/test_calibration.py` |
| Tracking / crop | `tests/test_tracker.py` |
| Cinemática | `tests/test_kinematics.py` |
| Validación | `tests/test_validation.py` |
| Estabilización | `tests/test_stabilizer.py` |
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
