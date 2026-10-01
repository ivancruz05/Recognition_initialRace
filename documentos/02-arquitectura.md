# Arquitectura

## Enfoque

El backend organiza sus módulos con arquitectura por capas y principios de arquitectura hexagonal (puertos y adaptadores). La estructura separa reglas de negocio, casos de uso, tecnología de persistencia y transporte HTTP.

El anteproyecto además propone un pipeline analítico Python (CLI con Click) para video, MediaPipe, OpenCV, Open3D/LiDAR y NumPy. Ese pipeline aún no existe en el checkout; su integración con Django queda como decisión arquitectónica pendiente. No se debe acoplar el dominio a las librerías de visión por computador.

```text
Cliente HTTP
    ↓
interfaces (views y serializers)
    ↓
application (casos de uso y DTOs)
    ↓
domain (entidades, reglas, excepciones y puertos)
    ↑
infrastructure (adaptadores Django/ORM y sesiones)
```

La flecha de infraestructura hacia el dominio representa que el adaptador implementa un puerto declarado por el dominio. El caso de uso depende de la abstracción `UserRepository`, no de una clase concreta de Django.

## Capas y responsabilidades

### `domain/` — núcleo

Contiene conceptos y reglas del negocio independientes del framework. En `accounts`, `UserAccount` es una dataclass con invariantes; `UserRepository` es el puerto; las excepciones describen fallos propios del dominio. Esta capa no importa Django ni DRF.

### `application/` — acciones del sistema

Contiene DTOs dataclass y casos de uso. `Login`, `Register` y `GetMe` coordinan el flujo utilizando el puerto del dominio. No conocen HTTP, modelos ORM ni la implementación del repositorio.

### `infrastructure/` — adaptadores externos

Implementa el puerto con Django ORM y las funciones de autenticación/sesión. Aquí ocurre el mapeo entre `UserAccount` y el modelo Django `User`; el modelo ORM no debe salir hacia las capas internas.

### `interfaces/` — adaptadores de entrada

Los serializers validan la forma del payload y lo convierten a DTOs de application. Las vistas conectan HTTP con los casos de uso y traducen excepciones de dominio a respuestas HTTP. Las rutas asocian URL y vista.

## Inyección y composición

Las vistas actúan como punto de composición: construyen `DjangoUserRepository` y lo inyectan en los casos de uso. Esta decisión mantiene application independiente de infraestructura. En una aplicación mayor, el montaje de dependencias podría trasladarse a un módulo de configuración dedicado.

## Flujo de autenticación

```text
POST /api/v1/auth/login/
  → LoginSerializer valida JSON y crea LoginInput
  → Login.execute(LoginInput)
  → UserRepository.verify_credentials(...)
  → DjangoUserRepository usa el backend de autenticación de Django
  → UserAccount se convierte a AuthOutput
  → la vista inicia la sesión y devuelve JSON público
```

El password viaja transitoriamente en los DTOs de entrada, pero no se incluye en `UserAccount` ni `AuthOutput`. Django lo procesa mediante `set_password`; la configuración actual prioriza Argon2 y conserva hashers anteriores para verificación.

## Separación prevista del análisis biomecánico

La propuesta académica separa la captura/extracción de landmarks, el cálculo de ángulos, la comparación con literatura y la visualización. El estado actual solo implementa cuentas y CRUD parcial de atletas en Django. Antes de integrar el pipeline de visión, se debe decidir si será una librería/CLI ejecutada por el backend, un worker asíncrono o un servicio separado; la elección depende del volumen de videos, duración, formato LiDAR y plataforma de despliegue.

Hay además una diferencia de entorno que resolver: el anteproyecto propone Python 3.12 para análisis, mientras que el entorno actual inspeccionado es Python 3.9.6 y no incluye MediaPipe, OpenCV, Open3D, NumPy o scikit-learn. No se debe asumir que todas estas dependencias se instalarán dentro del mismo entorno de Django; documentar la decisión antes de integrar.

La aplicación `analysis` actual es un stub no instalado, no ese pipeline. La diferencia entre el anteproyecto, el backend actual y los mockups se registra en [Requisitos, trazabilidad y datos](07-requisitos-y-trazabilidad.md).

## Flujo de excepciones

- Domain define errores como `InvalidAccountData`, `InvalidCredentials`, `EmailAlreadyRegistered` y `UserNotFound`.
- Application los propaga sin convertirlos a HTTP.
- Infrastructure traduce errores propios de Django cuando corresponda.
- Interfaces captura los errores de dominio y los convierte en status y cuerpos HTTP.
- Los errores de forma del payload son errores de DRF y se responden como 400.

## Decisión de estructura para modelos

`athletes` mantiene su modelo ORM en `infrastructure/models.py` y lo reexporta desde `apps/athletes/models.py` para el descubrimiento de Django. `accounts` conserva los modelos en `apps/accounts/models/`: la migración existente registra la ruta de `CustomUserManager`, por lo que moverla requiere una migración/ajuste deliberado. La diferencia es intencional y debe revisarse si se decide uniformar los módulos.

## Pruebas por capa

- Domain: invariantes y excepciones sin Django.
- Application: casos de uso con repositorio fake.
- Infrastructure: adaptador contra la base de datos de pruebas.
- Interfaces/API: endpoints, status HTTP y sesiones usando el cliente de DRF.

## Diagramas

Los diagramas ER y de comunicación se encuentran en [Modelo de datos y diagramas](06-modelado-y-diagramas.md). La matriz de requisitos, dependencias de datos y diferencias entre mockups e implementación están en [Requisitos, trazabilidad y datos](07-requisitos-y-trazabilidad.md).
