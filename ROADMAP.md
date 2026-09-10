# Roadmap - Reconocimiento de Posición de Arranque

## Visión General
Sistema de análisis automático de posición de sprint: sube video → ML analiza 2D → LiDAR da profundidad → comparación automática → predicciones.

---

## FLUJO PRINCIPAL

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  USUARIO    │    │  SISTEMA    │    │     ML      │    │  RESULTADO  │
│  sube video │───▶│  procesa    │───▶│  analiza    │───▶│  predicción │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     .r3d              frames           keypoints           reporte
     .mp4              + depth          2D + 3D             automático
```

---

## FASE 1: Proof of Concept ✅
**Objetivo:** Pipeline básico de video → pose → keypoints

| Componente | Estado | Archivo |
|------------|--------|---------|
| MediaPipe Pose (33 landmarks) | ✅ | `src/pose.py` |
| Depth map sampling | ✅ | `src/depth.py` |
| Fusión MediaPipe + LiDAR → 3D | ✅ | `src/fusion.py` |
| Point cloud generation (PLY) | ✅ | `src/ply.py` |
| Datos sintéticos para testing | ✅ | `src/synthetic.py` |
| Parser de archivos .r3d | ✅ | `r3d_parser.py` |

---

## FASE 2: Procesamiento Automático ✅
**Objetivo:** Subir video y obtener análisis automático

| Tarea | Estado |
|-------|--------|
| Parser de .r3d → frames + depth | ✅ |
| Extracción de keypoints de video | ✅ |
| Guardado de resultados | ✅ |

---

## FASE 3: Análisis Biomecánico ✅
**Objetivo:** Calcular métricas de posición de salida

| Métrica | Estado |
|---------|--------|
| Ángulo de rodilla | ✅ |
| Ángulo de cadera | ✅ |
| Ángulo de tobillo | ✅ |
| Ángulo de tronco | ✅ |
| Distancia entre pies | ✅ |
| Altura de cadera | ✅ |

---

## FASE 4: Comparación con Referencia ✅
**Objetivo:** Comparar automáticamente con posición óptima

| Tarea | Estado |
|-------|--------|
| Referencia óptima (literatura) | ✅ |
| Cálculo de errores | ✅ |
| Reporte de desviaciones | ✅ |

---

## FASE 5: Machine Learning para Predicciones ⏳
**Objetivo:** ML analiza video 2D para predecir rendimiento

### 5.1 Entrenamiento del Modelo
| Tarea | Estado |
|-------|--------|
| Recopilar dataset de videos de sprint | ⏳ |
| Extraer features de keypoints 2D | ⏳ |
| Etiquetar datos (tiempo, calidad) | ⏳ |
| Entrenar modelo de clasificación | ⏳ |
| Entrenar modelo de regresión (tiempo) | ⏳ |

### 5.2 Features para ML
| Feature | Descripción | Estado |
|---------|-------------|--------|
| `knee_angle_diff` | Diferencia rodilla delantera vs trasera | ⏳ |
| `hip_angle_front` | Ángulo cadera delantera | ⏳ |
| `trunk_inclination` | Inclinación del tronco | ⏳ |
| `height_ratio` | Proporción altura cadera/suelo | ⏳ |
| `foot_distance` | Distancia entre pies | ⏳ |
| `symmetry_score` | Simetría izquierda vs derecha | ⏳ |
| `velocity_features` | Velocidad de movimiento (frames) | ⏳ |

### 5.3 Predicciones
| Predicción | Tipo | Estado |
|------------|------|--------|
| Calidad de posición (1-10) | Clasificación | ⏳ |
| Tiempo estimado de reacción | Regresión | ⏳ |
| Errores comunes detectados | Clasificación multilabel | ⏳ |
| Recomendaciones personalizadas | Reglas + ML | ⏳ |

---

## FASE 6: Interfaz de Subida Automática ⏳
**Objetivo:** Subir video y obtener resultado automáticamente

| Tarea | Estado |
|-------|--------|
| Interfaz de subida de archivos | ⏳ |
| Procesamiento en background | ⏳ |
| Notificación de resultado | ⏳ |
| Historial de análisis | ⏳ |

---

## FASE 7: Dashboard de Análisis ⏳
**Objetivo:** Visualizar tendencias y predicciones

| Tarea | Estado |
|-------|--------|
| Gráficas de evolución por atleta | ⏳ |
| Comparación entre sesiones | ⏳ |
| Alertas de deterioro | ⏳ |
| Exportar reportes | ⏳ |

---

## Progreso General

| Fase | Estado | Descripción |
|------|--------|-------------|
| FASE 1 | ✅ | Pipeline básico |
| FASE 2 | ✅ | Procesamiento automático |
| FASE 3 | ✅ | Análisis biomecánico |
| FASE 4 | ✅ | Comparación con referencia |
| FASE 5 | ⏳ | ML para predicciones |
| FASE 6 | ⏳ | Interfaz de subida |
| FASE 7 | ⏳ | Dashboard |

**Progreso: 4/7 fases completadas (57%)**
