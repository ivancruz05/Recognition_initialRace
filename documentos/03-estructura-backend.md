# Estructura del backend

El proyecto Django está en `backend/`. La siguiente guía explica las carpetas presentes y su función en el estado actual.

```text
backend/
├── manage.py
├── pytest.ini
├── config/
│   ├── settings.py
│   └── urls.py
└── apps/
    ├── accounts/
    │   ├── models/
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   ├── interfaces/
    │   ├── migrations/
    │   └── test/
    ├── athletes/
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   ├── interfaces/
    │   ├── migrations/
    │   └── tests/
    └── analysis/          # esqueleto aún no activo
```

En la raíz del repositorio, `documentos/` contiene la descripción del alcance, arquitectura, estructura, flujos y diagramas del proyecto.

## Raíz de `backend/`

- `manage.py`: comandos de Django (`runserver`, `migrate`, `check`).
- `pytest.ini`: configura pytest-django, los settings y el `pythonpath` para ejecutar pruebas desde `backend/`.
- `config/settings.py`: aplicaciones instaladas, modelo de usuario, middleware, base de datos y hashers.
- `config/urls.py`: punto de montaje de rutas: administración, atletas y autenticación.

## `apps/accounts/`

| Carpeta/archivo | Función | Estado |
|---|---|---|
| `models/` | Modelo custom `User`, `UserType` y `CustomUserManager` | Implementado |
| `domain/` | `UserAccount`, excepciones y puerto `UserRepository` | Implementado |
| `application/` | `LoginInput`, `RegisterInput`, `AuthOutput`, `Login`, `Register`, `GetMe` | Implementado |
| `infrastructure/` | `DjangoUserRepository` y adaptador de sesiones | Implementado |
| `interfaces/` | Serializers, vistas HTTP y rutas | Implementado |
| `migrations/` | Historial de esquema de la cuenta | Implementado |
| `test/` | Fixtures y pruebas por capa/API (nombre actual singular) | Implementado |

## `apps/athletes/`

- `application/`: DTOs y casos de uso de creación y consulta.
- `infrastructure/`: modelo Django y repositorio concreto.
- `interfaces/`: serializers, `AthleteViewSet` y router DRF.
- `tests/`: pruebas de dominio, aplicación, infraestructura y API.
- `models.py`: reexporta el modelo de infraestructura para que Django lo detecte.

Actualmente expone creación mediante `POST /api/v1/athletes/` y consulta por id mediante `GET /api/v1/athletes/{id}/`.

## `apps/analysis/`

La carpeta contiene los archivos generados por Django, pero el modelo y la vista son stubs. Además, no está incluida en `INSTALLED_APPS` en la configuración actual. Por tanto, no se describe como funcionalidad analítica implementada.

El anteproyecto propone un pipeline independiente con Python 3.12, MediaPipe, OpenCV, Open3D, NumPy y Click. Ese paquete/pipeline aún no aparece en este checkout; el entorno existente para Django utiliza Python 3.9.6. La guía académica y las decisiones de integración están en [Base académica](00-base-anteproyecto.md) y [Arquitectura](02-arquitectura.md).

## Comandos de desarrollo

Ejecutados desde la raíz del repositorio:

```bash
cd backend
../.venv/bin/python manage.py check
../.venv/bin/pytest -q
```
