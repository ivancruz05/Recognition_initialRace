# Modelo de datos y diagramas de comunicación

Los diagramas de esta página describen el estado actual del repositorio. Las piezas todavía no implementadas se identifican como futuras o pendientes; no son parte del esquema actual.

## Diagrama entidad-relación actual

El dominio persistido del proyecto tiene dos modelos propios: `User` y `Athlete`. **Actualmente no existe una relación de clave foránea entre ellos.** El tipo de usuario (`admin` o `customer`) es una elección de campo, no una entidad separada.

```mermaid
erDiagram
    USER_ACCOUNT {
        bigint id PK
        varchar email UK
        varchar password "hash codificado por Django"
        varchar first_name
        varchar last_name
        varchar user_type "admin o customer"
        boolean is_active
        boolean is_staff
        boolean is_superuser
        datetime last_login
        datetime date_joined
    }

    ATHLETE {
        bigint id PK
        varchar first_name
        varchar last_name
        date date_of_birth
    }
```

El diagrama resume los campos relevantes de los modelos actuales. `User` hereda de `AbstractUser`, por lo que Django también administra relaciones con grupos y permisos; estas tablas internas del framework se omiten para mantener visible el modelo propio del proyecto. El valor guardado en `password` es un hash, no el password legible.

La tabla `USER_ACCOUNT` corresponde a `accounts_user`; `ATHLETE` corresponde a `athletes_athlete`. Los tipos y longitudes completos se consultan en los modelos y migraciones.

### Diferencia con los mockups

Las pantallas de referencia muestran documento, categoría, grupo, estado y cantidad de pruebas para los atletas. Esos atributos **no están en el modelo `Athlete` actual**. Se incluyen como requisitos por confirmar en [Requisitos, trazabilidad y datos](07-requisitos-y-trazabilidad.md), no como columnas existentes.

## Diagrama de comunicación del sistema

Este diagrama presenta cómo se comunican las capas para las funcionalidades actuales. El cliente visual aparece como externo y pendiente de incorporación al repositorio; puede sustituirse temporalmente por un cliente API durante las pruebas.

```mermaid
flowchart LR
    actor[Entrenador o usuario] --> client[Cliente web / API]
    client -->|HTTP y JSON| routes[URLs Django]
    routes --> views[Views]
    views --> serializers[Serializers DRF]
    serializers -->|DTO de entrada| app[Application: casos de uso]
    app -->|puerto UserRepository| domain[Domain: entidades y contratos]
    infra[Infrastructure: DjangoUserRepository] -. implementa .-> domain
    app --> infra
    infra -->|ORM y autenticación| db[(SQLite configurada actualmente)]
    views -->|login/logout de sesión| session[Sesión Django]
    session --> db
    views -->|DTO de salida / HTTP| client
```

La sesión se representa aparte de la persistencia del perfil porque `login()` y `logout()` gestionan el estado de autenticación de Django. En el login, el servidor devuelve la respuesta HTTP y actualiza la cookie de sesión.

Las flechas muestran comunicación en tiempo de ejecución. Aunque el caso de uso invoca el puerto del repositorio, la dependencia de código continúa invertida: `DjangoUserRepository` implementa el contrato definido en `domain/`.

## Mapa de casos de uso y estado

Se usa un actor genérico (`Cliente API`) porque la equivalencia de roles del mockup —por ejemplo, entrenador— con los roles del modelo (`admin` y `customer`) aún debe confirmarse.

```mermaid
flowchart LR
    client([Cliente API])

    subgraph current[Casos implementados]
        register((Registrar cuenta))
        login((Iniciar sesión))
        logout((Cerrar sesión))
        me((Consultar sesión actual))
        createAthlete((Crear atleta))
        getAthlete((Consultar atleta por id))
    end

    subgraph pending[Casos mostrados en mockups, pendientes]
        listAthletes((Listar y filtrar atletas))
        uploadVideo((Subir video de prueba))
        viewResults((Consultar resultados analíticos))
        reports((Generar reportes))
    end

    client --> register
    client --> login
    client --> logout
    client --> me
    client --> createAthlete
    client --> getAthlete
    client -. por definir .-> listAthletes
    client -. por definir .-> uploadVideo
    client -. por definir .-> viewResults
    client -. por definir .-> reports
```

El diagrama no implica que los casos pendientes tengan endpoints o permisos implementados. La matriz de requisitos contiene el detalle de su estado.

## Secuencia actual: inicio de sesión

```mermaid
sequenceDiagram
    actor Usuario
    participant Cliente as Cliente HTTP
    participant View as LoginView
    participant Serializer as LoginSerializer
    participant UseCase as Login (application)
    participant Port as UserRepository (domain)
    participant Adapter as DjangoUserRepository
    participant Auth as Django ModelBackend
    participant DB as Base de datos
    participant Session as Sesión Django

    Usuario->>Cliente: Ingresa email y password
    Cliente->>View: POST /api/v1/auth/login/
    View->>Serializer: is_valid(request.data)
    Serializer-->>View: LoginInput
    View->>UseCase: execute(LoginInput)
    UseCase->>Port: verify_credentials(email, password)
    Port->>Adapter: implementación del puerto
    Adapter->>Auth: authenticate(email, password)
    Auth->>DB: Consulta usuario y hash
    DB-->>Auth: Usuario o no encontrado
    Auth-->>Adapter: Usuario autenticado / None
    Adapter-->>UseCase: UserAccount o InvalidCredentials
    UseCase-->>View: AuthOutput
    View->>Session: login(request, user_id)
    Session->>DB: Guarda identidad en la sesión
    View-->>Cliente: 200 + datos públicos + cookie de sesión
```

Si el formato del payload no es válido, DRF responde 400 antes de ejecutar el caso de uso. Si las credenciales no coinciden, la vista traduce `InvalidCredentials` a 401.

## Secuencia actual: crear atleta

```mermaid
sequenceDiagram
    participant Cliente as Cliente HTTP
    participant Router as Router DRF
    participant View as AthleteViewSet.create
    participant Serializer as AthleteSerializer
    participant UseCase as CreateAthlete
    participant Entity as Athlete (domain)
    participant Port as AthleteRepository
    participant Adapter as DjangoAthleteRepository
    participant DB as Base de datos

    Cliente->>Router: POST /api/v1/athletes/
    Router->>View: create(request)
    View->>Serializer: Valida JSON
    Serializer-->>View: CreateAthleteInput
    View->>UseCase: execute(input)
    UseCase->>Entity: Construye y valida entidad
    UseCase->>Port: add(entity)
    Port->>Adapter: Implementación Django
    Adapter->>DB: Guarda fila Athlete
    DB-->>Adapter: id asignado
    Adapter-->>UseCase: Entidad persistida
    UseCase-->>View: AthleteOutput
    View-->>Cliente: 201 + representación pública
```

## Flujo analítico propuesto por el anteproyecto

El anteproyecto propone cargar video RGB estándar y LiDAR opcional, seleccionar frames en posición “set”, extraer pose, calcular ángulos, contrastarlos con literatura y mostrar recomendaciones. En el código actual `apps/analysis` es un esqueleto, no está activa en `INSTALLED_APPS` y no tiene modelos ni endpoints funcionales. Este flujo está definido académicamente, pero no implementado.

Después de recibir y verificar los archivos, se deberá definir el contrato de carga, el estado del procesamiento, persistencia y respuestas de la API. Flujo previsto, pendiente de diseño técnico:

```mermaid
flowchart LR
    user[Entrenador o investigador] -->|selecciona intento| ui[Interfaz visual - pendiente]
    ui -->|MP4/MOV y R3D opcional| api[API de análisis - pendiente]
    api --> usecase[Orquestación de análisis - por diseñar]
    usecase --> pose[Extracción de pose y landmarks - propuesta]
    pose --> biomech[Cálculo de ángulos - propuesta]
    biomech --> compare[Comparación y score - requiere validar referencias]
    compare --> result[results.json / resultados API - esquema por confirmar]
    source[(Video, R3D, medidas y protocolo suministrados)] -. datos por verificar .-> pose
```

El anteproyecto propone MediaPipe, OpenCV, Open3D, NumPy y un CLI con Click; no están presentes en el backend actual. El clasificador ML se plantea como fase posterior y no se dibuja como parte del flujo implementado. Esta vista es una guía para diseñar, no una declaración de arquitectura ya construida.
