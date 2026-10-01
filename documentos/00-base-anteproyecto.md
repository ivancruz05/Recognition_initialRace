# Base académica del sistema

## Fuente y prioridad

La fuente académica de referencia es **`Anteproyecto_SalidaArranque.docx`**, entregado por el equipo y localizado en `Downloads` durante la documentación. Los documentos técnicos de esta carpeta resumen esa fuente; el archivo original no se copia al repositorio.

Hasta que el director o el programa indique una versión aprobada más reciente, este anteproyecto define el problema, el alcance académico y la metodología esperada. El código muestra el avance real; los mockups son una referencia de interacción visual. Si hay diferencias, se registran aquí y se resuelven con el equipo académico antes de convertirlas en requisitos implementados.

## Identificación académica indicada en la fuente

- **Institución:** Universidad de Cundinamarca.
- **Unidad:** Facultad de Ingeniería, Programa de Ingeniería de Sistemas y Computación.
- **Título:** *Sistema de análisis y visualización de datos para el estudio del rendimiento en la salida de arranque de atletas*.
- **Autor que aparece en el documento:** Ivan Santiago Cruz Villarraga.
- **Director que aparece en el documento:** Campo Eli Castillo Eraso.
- **Lugar y año:** Fusagasugá, Cundinamarca, 2026.

## Problema y pregunta de investigación

El anteproyecto plantea que entrenadores e investigadores recopilan datos de la salida de arranque —tiempo de reacción, fuerza contra los bloques, ángulos articulares y velocidad de despegue—, pero la información suele quedar dispersa en planillas o reportes crudos. Esto dificulta comparar intentos y seguir la evolución del atleta. Se busca una alternativa que no dependa exclusivamente de laboratorios biomecánicos costosos.

**Pregunta formulada:** ¿cómo diseñar un sistema que procese video estándar y datos de profundidad LiDAR, calcule ángulos biomecánicos relevantes de la salida, los compare con referencias de literatura y genere interpretaciones útiles para entrenadores e investigadores?

## Objetivo general

Diseñar e implementar un sistema de análisis y visualización que procese, compare e interprete el rendimiento en la salida de arranque a partir de video y datos de profundidad, apoyado en visión por computador y aprendizaje automático.

## Objetivos específicos del anteproyecto

1. Detectar poses y extraer landmarks desde video estándar y archivos LiDAR.
2. Calcular ángulos de rodillas, caderas, tronco y tobillos.
3. Comparar los ángulos con rangos de la literatura y generar recomendaciones.
4. Proponer un clasificador de calidad de salida (`buena`, `regular`, `mala`) e identificar variables influyentes.
5. Diseñar un dashboard interactivo para visualizar indicadores, comparaciones e interpretaciones.

## Delimitación y datos indicados

- El análisis se limita a la **fase de salida de arranque**: posición de bloques y primeros instantes de carrera; no equivale a análisis general de toda una carrera.
- Entrada principal: videos estándar `MP4`/`MOV`.
- Entrada opcional: `.r3d` de iPhone con RGB y mapas LiDAR de profundidad en milímetros.
- El anteproyecto señala un conjunto de 10 atletas del programa de deportes de la Universidad de Cundinamarca, entre 1 y 3 intentos por atleta (aproximadamente 20 intentos), video Full HD y distancias LiDAR de 0,5 a 3 m.
- Para la posición “set”, propone seleccionar frames con al menos 25 landmarks detectados, visibilidad superior a 0,5 en rodillas y caderas y una flexión compatible con la posición de carga.
- La fuente informa consentimiento de los participantes. Antes de usar archivos reales se deben verificar los consentimientos, permisos y las condiciones de almacenamiento.

**Disponibilidad:** las cantidades y formatos anteriores son los declarados por el anteproyecto; no equivalen a datos ya verificados en el repositorio. En la inspección actual no se encontraron videos `MP4`/`MOV`, archivos `.r3d` ni datasets del proyecto dentro del checkout. Debe registrarse la recepción y el inventario real cuando el equipo suministre los archivos.

## Método analítico propuesto

### Pose y cálculo biomecánico

La propuesta usa MediaPipe Pose (33 landmarks), con `model_complexity=2` y confianza de detección mínima 0,5. Para la posición “set”, exige al menos 25 landmarks detectados y visibilidad mayor que 0,5 en ambas rodillas y caderas, además de flexión compatible con la posición de carga.

Los ángulos se calculan a partir de tres landmarks mediante producto punto:

```text
θ = arccos((AB · BC) / (|AB| × |BC|))
grados = radianes × (180 / π)
```

La propuesta los limita a 0°–180° y redondea a un decimal. Identifica la pierna delantera principalmente por el menor ángulo de rodilla y usa la posición horizontal del tobillo como criterio secundario en caso de empate. Las variables son rodilla delantera/trasera, cadera delantera/trasera, tronco y tobillo delantero/trasero.

### Comparación y score

El documento propone comparar ángulos con rangos de literatura y producir puntajes parciales entre 0 y 10: 10 dentro del rango; 7–9 para desviaciones de 1°–5°; 3–6 para 5°–15°; y 0–2 para más de 15° fuera del rango. El score global es el promedio de las siete variables ponderado por confianza de detección. También se proponen detalles por articulación, comparaciones y recomendaciones. Rangos consignados en el anteproyecto:

| Variable | Rango propuesto |
|---|---:|
| Rodilla delantera | 80°–100° |
| Rodilla trasera | 110°–150° |
| Cadera delantera | 45°–70° |
| Cadera trasera | 85°–115° |
| Tronco | 15°–30° |
| Tobillo delantero | 75°–85° |
| Tobillo trasero | 75°–85° |

Estos son parámetros propuestos por la fuente, no valores validados por el software actual. Las bandas de puntuación indicadas se solapan exactamente en una desviación de 5°; ese límite debe aclararse antes de implementar el score. También hay que comprobar las referencias bibliográficas, su aplicabilidad a la población y el protocolo de medición antes de presentarlos como criterio clínico/deportivo.

### Aprendizaje automático propuesto

- Clasificación de calidad basada en siete ángulos: `mala` (<50), `regular` (50 a <70), `buena` (≥70).
- Features propuestas: `front_knee`, `rear_knee`, `front_hip`, `rear_hip`, `trunk`, `front_ankle`, `rear_ankle`; las medidas corporales serían opcionales.
- Random Forest aparece como algoritmo base; scikit-learn/XGBoost como opciones.
- La validación propuesta es k-fold con k=5 y métricas accuracy, precision, recall, F1, matriz de confusión y curva ROC multiclase.
- El anteproyecto reconoce que 10 atletas y aproximadamente 20 intentos no bastan para entrenar y validar un modelo robusto; estima necesitar 50–100 o más muestras etiquetadas por expertos.
- Por tanto, la clasificación ML se documenta como propuesta condicionada a la disponibilidad de datos etiquetados suficientes. No se deben anunciar métricas de desempeño antes de esa validación.

## Flujo metodológico y tecnologías

La metodología es aplicada, iterativa e incremental. Propone las fases: extracción de datos, cálculo biomecánico, análisis comparativo y visualización; cada componente se probaría antes de integrarlo.

| Componente analítico propuesto | Tecnología indicada |
|---|---|
| Lenguaje de análisis | Python 3.12 |
| Estimación de pose | MediaPipe Pose |
| Video | OpenCV 4.8 |
| LiDAR/nubes de puntos | Open3D |
| Cálculos numéricos | NumPy |
| CLI | Click |
| ML, pendiente | scikit-learn / XGBoost |

El entorno actual inspeccionado es Python 3.9.6 y contiene el backend Django/DRF; no tiene el código ni las dependencias de visión por computador listadas arriba. Antes de integrar ambos lados se debe decidir compatibilidad de versiones y si el análisis será una biblioteca/CLI separada o un servicio de procesamiento llamado por el backend.

## Organización de datos propuesta

El anteproyecto sugiere una estructura de carpetas por atleta con `videos/`, `r3d/`, `measurements/` y `analysis/results.json`. Esta es una organización propuesta para archivos, **no el esquema relacional actual de Django**. Debe definirse una convención de IDs para vincular atleta, intento, archivo de entrada y resultado sin depender de nombres ficticios.

## Ética y referencias

La fuente indica consentimiento informado y anonimización con código numérico/nombre ficticio. Estos aspectos deben cotejarse con los documentos reales antes de procesar imágenes o datos personales.

La bibliografía incluida en el anteproyecto todavía tiene referencias incompletas. Completar autores, título, revista/editorial, año, volumen, páginas y DOI/URL, y validar que cada rango biomecánico atribuido corresponda realmente a esa fuente.
