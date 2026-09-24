# Roadmap - Software de Análisis de Video por Drones Autónomos

## Visión General
Sistema para evaluar variables biomecánicas de atletas (postura, velocidad, longitud de zancada y cadencia) a partir de video capturado por un dron autónomo (DJI Spark) en el CADI de atletismo.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  VIDEO      │───▶│  ESTABILIZ. │───▶│  TRACKING   │───▶│  POSE ROI   │
│  dron .mp4  │    │  + ArUco    │    │  YOLOv8     │    │  MediaPipe  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                               │
                    ┌──────────────────────────────────────────┘
                    ▼
            ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
            │  CALIBRACIÓN│───▶│  CINEMÁTICA │───▶│  VALIDACIÓN │
            │  px -> m    │    │  v, zancada,│    │  vs. manual │
            │             │    │  cadencia   │    │  error %    │
            └─────────────┘    └─────────────┘    └─────────────┘
```

---

## FASE 1 - Diseño y desarrollo del software ✅

| Componente | Estado | Archivo principal |
|------------|--------|-------------------|
| Calibración ArUco px→m | ✅ | `drone_analysis/infrastructure/calibration/aruco.py` |
| Detección y seguimiento atleta (YOLOv8 + ByteTrack) | ✅ | `drone_analysis/infrastructure/tracking/athlete_tracker.py` |
| Estimación de pose en ROI (MediaPipe) | ✅ | `drone_analysis/infrastructure/pose/detector.py` |
| Estabilización de video de dron | ✅ | `drone_analysis/infrastructure/video/stabilizer.py` |
| Pipeline end-to-end | ✅ | `drone_analysis/application/drone_pipeline.py` |

---

## FASE 2 - Pruebas del software ✅

| Tarea | Estado | Detalle |
|-------|--------|---------|
| Tests unitarios de calibración | ✅ | `tests/test_calibration.py` |
| Tests unitarios de tracking/crop | ✅ | `tests/test_tracker.py` |
| Tests unitarios de cinemática | ✅ | `tests/test_kinematics.py` |
| Tests unitarios de validación | ✅ | `tests/test_validation.py` |
| Tests unitarios de estabilización | ✅ | `tests/test_stabilizer.py` |
| CLI funcional | ✅ | `drone --help` |

---

## FASE 3 - Validación con grupo piloto ⏳

| Tarea | Estado | Detalle |
|-------|--------|---------|
| Captura con dron DJI Spark y 20 estudiantes | ⏳ | Pendiente de disponibilidad de video |
| Registro manual cuadro a cuadro | ⏳ | Plantilla generada por `drone groundtruth` |
| Comparación automática vs. manual | ✅ | `drone_analysis/analysis/validation.py` |
| Cálculo de error absoluto y porcentual | ✅ | `drone validate <results> <ground_truth>` |
| Criterios ISO/IEC 25010 | ✅ | Bandas EXCELLENT / ACCEPTABLE / LIMIT / UNACCEPTABLE |

---

## Comandos CLI

```bash
# Calibrar con ArUco
drone calibrate reference.jpg -o calibration.json

# Analizar video
drone analyze video.mp4 -c calibration.json -o output/

# Generar video anotado
drone annotate video.mp4 -c calibration.json -o annotated.mp4

# Crear plantilla de anotación manual
drone groundtruth video.mp4 -o ground_truth.json

# Validar resultados
drone validate output/results.json ground_truth.json -o validation.json
```

---

## Dependencias principales

- `opencv-contrib-python` (ArUco + video)
- `mediapipe` (pose 33 landmarks)
- `ultralytics` (YOLOv8 + tracker)
- `numpy`, `scipy`
- `click`, `pytest`

## Progreso general

**Fases completadas: 2/3 (66%)** — en espera de videos del dron para la validación de campo.
