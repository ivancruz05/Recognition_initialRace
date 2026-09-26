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

## ARQUITECTURA

Repositorio modularizado por preocupación (no por capa técnica):

| Módulo | Responsabilidad |
|--------|-----------------|
| `detection/` | Video → métricas biomecánicas. `metrics/` = math pura, `vision/` = adaptadores cv2/mediapipe/ultralytics |
| `training/` | Dataset sintético, features, entrenamiento del baseline y notebooks |
| `backend/` | API HTTP (FastAPI). Solo traduce HTTP ↔ `detection` |
| `frontend/` | Cliente web (placeholder) |

Regla de dependencia: `detection/metrics/` no importa `detection/vision/`.
Detalle completo en [README.md](README.md).

---

## FASE 1 - Diseño y desarrollo del software ✅

| Componente | Estado | Archivo principal |
|------------|--------|-------------------|
| Calibración ArUco px→m | ✅ | `detection/vision/calibration.py` |
| Detección y seguimiento atleta (YOLOv8 + ByteTrack) | ✅ | `detection/vision/tracker.py` |
| Estimación de pose en ROI (MediaPipe) | ✅ | `detection/vision/pose.py` |
| Estabilización de video de dron | ✅ | `detection/vision/stabilizer.py` |
| Pipeline end-to-end | ✅ | `detection/pipeline.py` |

---

## FASE 2 - Pruebas del software ✅

| Tarea | Estado | Detalle |
|-------|--------|---------|
| Tests unitarios de calibración | ✅ | `tests/detection/test_calibration.py` |
| Tests unitarios de tracking/crop | ✅ | `tests/detection/test_tracker.py` |
| Tests unitarios de cinemática | ✅ | `tests/detection/test_kinematics.py` |
| Tests unitarios de validación | ✅ | `tests/detection/test_validation.py` |
| Tests unitarios de estabilización | ✅ | `tests/detection/test_stabilizer.py` |
| CLI funcional | ✅ | `drone --help` |

---

## FASE 3 - Validación con grupo piloto ⏳

| Tarea | Estado | Detalle |
|-------|--------|---------|
| Captura con dron DJI Spark y 20 estudiantes | ⏳ | Pendiente de disponibilidad de video |
| Registro manual cuadro a cuadro | ⏳ | Plantilla generada por `drone groundtruth` |
| Comparación automática vs. manual | ✅ | `detection/metrics/validation.py` |
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
