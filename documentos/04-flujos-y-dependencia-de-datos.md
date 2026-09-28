# Flujos y dependencia de datos

## Endpoints actuales

Las rutas se montan desde `config/urls.py`.

Los modelos ER y los diagramas de comunicación/secuencia asociados están en [Modelo de datos y diagramas](06-modelado-y-diagramas.md).

| Método | Ruta | Función | Resultado esperado |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | Crea cuenta y abre sesión | 201; datos públicos de la cuenta |
| `POST` | `/api/v1/auth/login/` | Valida credenciales y abre sesión | 200; 401 si no son válidas |
| `POST` | `/api/v1/auth/logout/` | Cierra sesión | 200 |
| `GET` | `/api/v1/auth/me/` | Consulta la cuenta de la sesión | 200; 401 si no hay sesión |
| `POST` | `/api/v1/athletes/` | Crea atleta | 201; 400 si la entrada es inválida |
| `GET` | `/api/v1/athletes/{id}/` | Consulta atleta por id | 200; 404 si no existe |

El flujo por sesión no emite JWT. Los clientes web deben manejar cookies de sesión y protección CSRF en solicitudes mutables autenticadas, como `POST logout/`.

## Contrato de datos descrito en el anteproyecto

La propuesta ya especifica tipos de entrada y resultados previstos; la estructura se debe cotejar con los archivos reales al recibirlos:

| Entrada/salida | Especificación indicada | Estado en la implementación |
|---|---|---|
| Video RGB | `MP4`/`MOV`; salida de arranque; mínimo 30 frames en posición “set” | No existe carga/procesamiento de video en backend |
| Profundidad opcional | `.r3d` de iPhone, RGB sincronizado con mapas de profundidad en milímetros | No existe parser LiDAR activo en el checkout |
| Medidas del atleta | Estatura, ancho de hombros, longitud de torso, entre otras | El modelo Athlete actual solo persiste nombre, apellido y fecha de nacimiento |
| Pose | 33 landmarks; propuesta de umbrales de visibilidad para seleccionar frames | MediaPipe no está integrado en el backend actual |
| Resultados | `angles`, `quality_score`, `quality_details`, `recommendations`, `comparisons`, `measurements` | No hay entidad, DTO ni endpoint de análisis implementado |

El anteproyecto declara 10 atletas, de 1 a 3 intentos por atleta (~20 intentos), Full HD y LiDAR opcional entre 0,5 y 3 m. **Es una cantidad declarada en la propuesta, no una verificación de que los archivos estén disponibles.** No se encontraron videos, archivos `.r3d` ni datasets de análisis en el repositorio inspeccionado; confirmar recepción e inventario con el equipo.

El documento propone organizar datos en `data/athletes/{codigo}/videos/`, `r3d/`, `measurements/` y `analysis/results.json`. Es una estructura de archivos propuesta, no un modelo de tablas Django. Antes de implementar se debe definir un identificador estable que relacione cada intento con sus archivos, mediciones y resultado.

## Trabajo que puede adelantarse

- Contratos HTTP, autenticación y administración básica.
- Estructura técnica para recibir trabajos de análisis sin acoplar reglas de negocio a librerías CV.
- Mockups y navegación visual alrededor de la salida de arranque, con datos de muestra marcados como demostración.
- Pruebas de interfaces, estados de carga/error y contratos con datos sintéticos.
- Registro de fuente, versión y consentimiento por cada lote de datos cuando se reciba.

## Validaciones necesarias antes del procesamiento real

1. Confirmar que el dataset real corresponde a la muestra descrita: cantidad de atletas/intentos, tipos de archivos y metadatos.
2. Revisar calidad, orientación, sincronización, calibración y distancia de cámara/LiDAR.
3. Verificar consentimientos, anonimización, permisos de uso, retención y acceso a videos.
4. Validar con especialista los landmarks, ángulos, rangos de literatura y score.
5. No entrenar ni declarar métricas de ML con ~20 intentos: el anteproyecto propone al menos 50–100 muestras etiquetadas por expertos.

## Trazabilidad académica

Para cada lote de datos, registrar fuente, fecha de recepción, versión, esquema, autorización/consentimiento, transformaciones, exclusiones y criterios de evaluación. Los resultados de la sustentación deben poder asociarse al conjunto y al código utilizados.
