# Drone Sprint Analysis

Evalúa variables biomecánicas (postura, velocidad, longitud de zancada y cadencia) a partir de video capturado por un dron autónomo (DJI Spark) en el CADI de atletismo.

## Estructura

El proyecto está modularizado por preocupación, no por capa técnica. Cada módulo se lee solo y se puede borrar sin tocar los demás.

| Módulo | Qué contiene | Qué NO contiene |
|--------|--------------|-----------------|
| `detection/` | Todo lo que convierte video en métricas biomecánicas: entidades, matemática pura, adaptadores de visión, pipelines, CLI | HTTP, entrenamiento de modelos |
| `training/` | Generación de datasets sintéticos, features, entrenamiento del baseline, notebooks | Lógica de detección, HTTP |
| `backend/` | API HTTP (FastAPI). Solo traduce HTTP ↔ `detection` | Cualquier cálculo biomecánico |
| `frontend/` | Cliente web (placeholder, sin scaffold todavía) | — |

### `detection/` en detalle

```
detection/
├── entities.py        dataclasses (PoseLandmarks, SprintMetrics, BodyMeasurements, ...)
├── constants.py       tablas de landmarks y proporciones de referencia
├── interfaces.py      ABCs: PoseDetectorInterface, BodyMeasurementInterface
├── metrics/           matemática pura — sin cv2, sin mediapipe, sin I/O
├── vision/            los únicos módulos que tocan cv2 / mediapipe / ultralytics
├── pipeline.py        orquestación end-to-end (DroneAnalyzer)
├── service.py         AnalysisService: análisis + mediciones
├── pipelines.py       pipelines especializados (MeasurementPipeline, AnalysisPipeline)
└── cli.py             comandos click
```

Regla de dependencia: `metrics/` no importa `vision/`. Si necesitas algo de `vision/` dentro de `metrics/`, es señal de que falta un caso de uso en el pipeline.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"          # librería + tests
pip install -e ".[dev,backend]"  # + FastAPI para el backend
```

## Uso

### CLI

```bash
drone --help

# Calibrar con ArUco
drone calibrate reference.jpg -o calibration.json

# Analizar video
drone analyze video.mp4 -c calibration.json -o output/

# Generar video anotado
drone annotate video.mp4 -c calibration.json -o annotated.mp4

# Plantilla de anotación manual
drone groundtruth video.mp4 -o ground_truth.json

# Validar contra ground truth
drone validate output/results.json ground_truth.json -o validation.json

# Dataset sintético + entrenamiento
drone ml-generate --athletes 200
drone ml-train data/synthetic_ml/trials.csv
```

### API HTTP

```bash
uvicorn backend.main:app --reload
```

| Método | Ruta | Qué hace |
|--------|------|----------|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/api/v1/analyze` | `video` + (`calibration` \| `pixels_per_meter`) → variables biomecánicas |
| `POST` | `/api/v1/measurements` | `video` + `known_height_cm` → medidas corporales |

Documentación interactiva: `http://localhost:8000/docs`

## Tests

```bash
pytest              # 25 tests
pytest tests/detection -q
pytest tests/training -q
```

## Dependencias

- `opencv-contrib-python` — ArUco + video
- `mediapipe` — pose de 33 landmarks
- `ultralytics` — YOLOv8 + ByteTrack
- `numpy`, `scipy`, `pandas`, `scikit-learn`, `joblib`
- `click`, `pytest`
- `fastapi`, `uvicorn` (extra `backend`)

## Estado

Fases 1 y 2 del [ROADMAP.md](ROADMAP.md) completas. La fase 3 (validación con grupo piloto de 20 estudiantes) está pendiente de disponibilidad de video del dron.
