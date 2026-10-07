# METODOLOGÍA DE AVANCE

## Alcance actual

El desarrollo implementa un flujo local para observar la técnica de carrera desde
una vista lateral. La captura en vivo utiliza el iPhone como Continuity Camera
conectada al Mac y accesible mediante OpenCV. Como alternativa, se analizan videos
grabados en formato MP4 o MOV.

Cada sesión corresponde a un atleta. La persona usuaria proporciona un código
manual para identificarlo; el sistema no realiza reconocimiento de identidad ni
selección automática entre varios atletas.

## Procedimiento

1. Ubicar el teléfono de lado respecto al atleta y conectar Continuity Camera al
   Mac, o seleccionar un archivo MP4/MOV existente.
2. Iniciar una sesión con un código de atleta y un destino CSV.
3. En captura en vivo, verificar el esqueleto y esperar cinco frames consecutivos
   con ángulos inferiores disponibles; luego pulsar `t`. `s` finaliza y `q`
   detiene.
4. Conservar el video MP4 original sin anotaciones desde el inicio de la captura,
   y crear un manifiesto JSON de salida/estado junto a los artefactos.
5. Aplicar MediaPipe Pose y calcular ángulos 2D, conservando por frame las
   coordenadas normalizadas y visibilidad de landmarks, ángulos disponibles y
   estados de pose en un CSV incremental.

## Arquitectura y herramientas

El dominio (`detection/domain/`) define entidades, puertos, excepciones y cálculo
geométrico de ángulos sin dependencias de infraestructura. La aplicación
(`detection/application/`) coordina el procesamiento de una sesión. Los
adaptadores (`detection/infrastructure/`) proporcionan fuentes de cámara y
archivo, detección/análisis MediaPipe y escritura CSV. La interfaz local se
ejecuta con `python -m detection`.

## Límites de interpretación

Los ángulos son proyecciones bidimensionales por frame. No se realiza calibración
métrica de cámara ni se calculan velocidad, distancia, longitud de zancada o
cadencia. La posición lateral y las condiciones de captura deben mantenerse
razonablemente constantes para facilitar la observación; no convierten los
resultados en medidas del espacio real.

La condición “pose lista” solo indica que se pueden calcular ángulos de cadera,
rodilla y tobillo en al menos un lado; no valida la orientación lateral. Los
archivos de cada intento deben conservar el mismo nombre base (`.mp4` y `.csv`)
y usar códigos anónimos únicos de atleta/sesión. Las etiquetas humanas aún no
están definidas ni registradas; se acordarán antes de construir cualquier modelo.

El alcance no incluye una aplicación móvil, Django, dron, LiDAR, YOLO, tracking,
estabilización, ArUco ni modelos o métricas ML legacy. La verificación técnica se
realiza mediante las pruebas automatizadas del dominio, aplicación,
infraestructura, CLI y reglas de capas.

## Protección de datos

Antes de capturar participantes, obtener consentimiento informado, usar códigos
anónimos, restringir el acceso a videos/CSV/manifiestos y acordar retención y eliminación.
El MVP no automatiza permisos ni almacenamiento seguro; esta responsabilidad debe
resolverse antes de la recolección de datos personales.
