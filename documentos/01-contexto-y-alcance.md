# Contexto, objetivo y alcance

## Base académica

El proyecto se basa en el anteproyecto *Sistema de análisis y visualización de datos para el estudio del rendimiento en la salida de arranque de atletas*, de la Universidad de Cundinamarca. El resumen de problema, objetivos y metodología está en [Base académica del sistema](00-base-anteproyecto.md). Ese documento es la referencia para el alcance académico; el código describe qué está implementado y los mockups sirven como propuesta de interfaz.

## Problema

El anteproyecto identifica que entrenadores e investigadores recopilan información de la salida de arranque —como reacción, fuerza contra los bloques, ángulos articulares y velocidad de despegue—, pero esta queda dispersa en planillas o reportes crudos. Esto dificulta comparar intentos y hacer seguimiento longitudinal, especialmente donde no hay acceso constante a laboratorios biomecánicos especializados.

La pregunta de investigación del documento es cómo procesar video estándar y profundidad LiDAR para calcular ángulos de la salida, compararlos con literatura y producir interpretaciones útiles para entrenadores e investigadores.

## Objetivo general

Diseñar e implementar un sistema de análisis y visualización del rendimiento en la salida de arranque mediante video y datos de profundidad, visión por computador y aprendizaje automático.

## Alcance funcional propuesto

1. Ingerir video estándar (`MP4`/`MOV`) y, opcionalmente, archivos LiDAR `.r3d` de iPhone.
2. Detectar la pose y seleccionar frames representativos de la posición “set”.
3. Calcular ángulos de rodillas, caderas, tronco y tobillos.
4. Comparar con referencias biomecánicas, score/recomendaciones y clasificación ML si los datos etiquetados lo permiten.
5. Presentar los resultados en un dashboard para entrenadores e investigadores.

La fase de salida de arranque es el foco. Los mockups muestran además pantallas y conceptos más amplios —pruebas de otras distancias, biblioteca, reportes y administración—; se deben tratar como alcance por confirmar, no expandir el objetivo sin aprobación.

## Datos: declarados y realmente disponibles

El anteproyecto declara 10 atletas, entre 1 y 3 intentos por atleta (~20), videos Full HD y LiDAR opcional a 0,5–3 m; también informa que se firmaron consentimientos. **Estos datos y condiciones están descritos en la propuesta, pero los archivos fuente no se encontraron en el repositorio inspeccionado.** Se confirmarán al recibir el conjunto real, su esquema y los consentimientos.

Los valores de rangos, umbrales de score y clases ML son propuestas del anteproyecto, no resultados validados del sistema. La misma propuesta advierte que ~20 intentos son insuficientes para un clasificador robusto y plantea obtener al menos 50–100 muestras etiquetadas por expertos.

## Estado de implementación observado

| Área | Estado actual |
|---|---|
| Backend Django/DRF | Base técnica implementada |
| Cuentas y sesiones | Registro, login, logout y consulta actual con pruebas |
| Atletas | Creación y consulta por id, con pruebas |
| Procesamiento de pose, ángulos, score y recomendaciones | No implementado en el checkout actual |
| Machine learning | Propuesto; no implementado y requiere más muestras etiquetadas |
| Dashboard | Mockups disponibles; no hay frontend en el checkout actual |
| Dataset del anteproyecto | Declarado en el documento; archivos no encontrados en el repositorio inspeccionado |

La app Django `analysis` existe como esqueleto, pero no está registrada como aplicación activa y aún no implementa análisis.

## Trabajo que puede adelantarse

- Autenticación, administración básica y contratos de API.
- Estructura de atletas y diseño del almacenamiento, sin agregar atributos ficticios.
- Mockups, navegación y estados visuales basados en la fase de salida de arranque.
- Acordar un contrato de resultados y un esquema para los archivos de entrada.
- Pruebas con datos sintéticos, siempre identificados como tales y sin presentarlos como validación deportiva.

## Trabajo que depende de los datos y validaciones

- Confirmar calidad, formato, calibración, orientación de cámara, sincronización RGB/profundidad y correspondencia de intentos.
- Validar los landmarks y selección de frames “set”.
- Validar fórmulas, referencias, score y recomendaciones con el director/especialistas.
- Entrenar/evaluar ML solo con suficientes muestras y etiquetas expertas.
- Definir privacidad, consentimiento, anonimización, retención y acceso a video/datos personales.

## Fuente detallada

Para identificación académica, objetivos específicos, metodología y parámetros propuestos, consultar [Base académica del sistema](00-base-anteproyecto.md). Las diferencias entre mockups y backend están registradas en [Requisitos y trazabilidad](07-requisitos-y-trazabilidad.md).
