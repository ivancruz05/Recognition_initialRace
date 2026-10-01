# Requisitos, trazabilidad y datos

Este documento vincula lo visible en los mockups con la implementación existente y deja identificadas las decisiones que requieren requisitos confirmados o datos suministrados.

## Matriz de funcionalidades

| ID | Funcionalidad | Evidencia en el repositorio | Estado |
|---|---|---|---|
| RF-01 | Registrar cuenta con email y password | `accounts` serializer, caso de uso, repositorio, vista y pruebas API | Implementado |
| RF-02 | Iniciar/cerrar sesión y consultar cuenta actual | Rutas `/auth/login/`, `/auth/logout/`, `/auth/me/` | Implementado |
| RF-03 | Crear atleta con nombre, apellido y fecha de nacimiento | `POST /api/v1/athletes/` y pruebas API | Implementado |
| RF-04 | Consultar atleta por identificador | `GET /api/v1/athletes/{id}/` y pruebas API | Implementado |
| RF-05 | Listar, filtrar, editar o archivar atletas | Aparece en los mockups; no está implementado por el endpoint actual | Pendiente de requisitos |
| RF-06 | Recibir MP4/MOV y LiDAR opcional, procesar salida de arranque | Definido en anteproyecto; `apps/analysis` es un esqueleto | Especificado; implementación pendiente de datos y diseño técnico |
| RF-07 | Extraer pose y calcular ángulos de rodilla, cadera, tronco y tobillo | MediaPipe/ángulos descritos en anteproyecto; sin módulo actual | Propuesto; implementación y validación pendientes |
| RF-08 | Generar reportes, biblioteca y configuración institucional | Aparece en los mockups; no hay módulos funcionales correspondientes | Pendiente de priorizar frente al alcance académico |
| RF-09 | Dashboard de salida de arranque con indicadores, comparación e interpretación | Objetivo específico del anteproyecto y mockups | Diseño visual adelantable; integración pendiente |
| RF-10 | Comparar ángulos con rangos y generar score/recomendaciones | Rangos y estrategia de score propuestos en anteproyecto | Pendiente de validación científica y técnica |
| RF-11 | Clasificar calidad `buena`, `regular`, `mala` con ML | Propuesto en anteproyecto; se requieren 50–100+ muestras etiquetadas | Pendiente; ~20 intentos declarados son insuficientes |

Los IDs son identificadores de trabajo para trazabilidad y no reemplazan la numeración que exija la guía institucional.

## Diferencias detectadas entre mockups y backend

| Información mostrada en los mockups | Estado del backend | Acción necesaria |
|---|---|---|
| Documento/identificación del atleta | No existe en el modelo `Athlete` | Confirmar necesidad, tipo, unicidad y reglas de privacidad |
| Categoría, grupo y estado del atleta | No existen como campos/relaciones del modelo actual | Definir vocabulario, relaciones y responsables de la información |
| Historial de pruebas y métricas | No hay modelos de pruebas ni resultados | Definir esquema tras conocer protocolo y fuente de datos |
| Velocidad, cadencia, longitud de zancada y postura | Son conceptos de los mockups, no resultados actuales del backend | Validar definiciones, unidades, cálculo y criterios de interpretación |
| Video de prueba y estado de procesamiento | No existe endpoint, entidad o servicio activo de análisis | Acordar formato, almacenamiento, límites y pipeline de procesamiento |
| Usuario “entrenador/administrador” | El modelo actual maneja `user_type` = `admin` o `customer` | Confirmar equivalencia de roles y permisos antes de ampliar autorización |
| Videos “capturados con drones” | Una frase de los mockups difiere del anteproyecto (video estándar y LiDAR opcional de iPhone) | Confirmar dispositivos de captura; afecta perspectiva, escala, profundidad y procesamiento |
| Alcance de las pruebas | Mockups muestran 10 m y otras distancias; el anteproyecto se limita a la fase de salida de arranque | Priorizar la salida de arranque o aprobar formalmente la ampliación |
| ML y categorías | Mockups muestran evaluaciones ilustrativas; el anteproyecto propone clases/umbrales y reconoce que la muestra es pequeña | No publicar categorías ni precisión hasta obtener etiquetas expertas y validar |
| Stack de análisis | Anteproyecto requiere Python 3.12 y librerías CV/ML; el entorno actual inspeccionado es Python 3.9.6 con Django/DRF | Decidir si el pipeline será separado, si se actualiza entorno o cómo interoperan |
| Consentimiento y anonimización | El anteproyecto declara consentimientos y códigos ficticios; los documentos no están en el repositorio | Confirmar autorizaciones y políticas antes de incorporar videos reales |

## Plantilla de diccionario de datos

Completar una fila por campo recibido o calculado. No fijar unidades o rangos basándose solo en los mockups.

| Campo | Definición | Tipo/formato | Unidad | Fuente | Regla/validación | Sensibilidad | Estado |
|---|---|---|---|---|---|---|---|
| Por completar | Por confirmar | Por confirmar | No aplica/por confirmar | Suministrada o calculada | Por confirmar | Por clasificar | Pendiente |

## Preguntas previas al análisis

1. ¿Se entregará el conjunto descrito (10 atletas, ~20 intentos)? ¿Cuál es su inventario real y versión?
2. ¿Cómo se identifica cada intento y se asocian video MP4/MOV, R3D, medidas y resultado?
3. ¿Se dispone de LiDAR y archivos `.r3d` o será opcional/no utilizado?
4. ¿Qué posiciones de cámara, escala y condiciones de captura permiten interpretar las coordenadas de pose?
5. ¿Quién valida rangos de literatura, scores y etiquetas ML? ¿Hay suficientes muestras etiquetadas?
6. ¿Se pueden verificar consentimientos, anonimización y condiciones de almacenamiento?
7. ¿Los números de los mockups son datos demostrativos o mediciones reales verificadas?

## Requisitos no funcionales observados

- Las reglas de negocio deben permanecer independientes de Django y DRF.
- Los passwords se almacenan como hash usando el hasher preferido configurado en Django; no se deben documentar ni exportar en texto plano.
- Las vistas devuelven solo DTOs públicos, nunca modelos ORM o hashes.
- Las solicitudes mutables autenticadas con sesión deben considerar protección CSRF.
- Los análisis y resultados deben ser trazables a la versión de datos y del procesamiento cuando esa funcionalidad se diseñe.
- Las recomendaciones biomecánicas deben comunicar sus referencias y limitaciones; no sustituyen el juicio del entrenador.
- La clasificación ML no debe presentarse como validada con la muestra pequeña declarada en el anteproyecto.

## Cómo mantener la trazabilidad

Al confirmar cada requisito, agregar su fuente (propuesta, entrevista, protocolo o conjunto de datos), criterio de aceptación, capa responsable, pruebas asociadas y estado. Cuando los mockups cambien, registrar si el cambio implica modificar requisitos, modelos o endpoints.

## Glosario breve

| Término | Significado en el proyecto |
|---|---|
| Entidad de dominio | Objeto Python que representa un concepto y valida sus invariantes; no es el modelo ORM. |
| DTO | Dataclass que transporta datos entre capas, como `LoginInput` o `AuthOutput`. |
| Puerto | Contrato abstracto del dominio, como `UserRepository`. |
| Adaptador | Implementación tecnológica del puerto, como `DjangoUserRepository`. |
| Sesión | Estado de autenticación que Django mantiene entre solicitudes; no es un JWT. |
| Hash de password | Representación unidireccional almacenada por Django; no permite recuperar el password original. |
| Dato suministrado | Información de entrada cuya estructura, semántica y uso deben verificarse con su fuente antes de diseñar el análisis. |
