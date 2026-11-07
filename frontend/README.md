# CADI · Fase II — Frontend

Frontend en Next.js (App Router + TypeScript + Tailwind CSS + shadcn/ui) para el
backend Django REST del monitoreo de atletas iniciales.

## Requisitos

- Node.js 18.18+ y npm
- Backend corriendo primero:

```bash
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py runserver 0.0.0.0:8001
```

El backend permite el origen `http://localhost:3001` (CORS).

## Ejecutar

```bash
npm install
npm run dev
```

Abre <http://localhost:3001>.

El servidor de desarrollo escribe sus artefactos en `.next-dev/`; el build de
producción usa `.next/` para que ambos no compartan chunks.

Build de producción:

```bash
npm run build
npm start
```

## Configuración

La URL del backend se define con `NEXT_PUBLIC_API_URL`
 (por defecto `http://localhost:8001/api/v1`):

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
```

## Estructura

- `app/` — páginas (App Router): login, `/dashboard`, sesiones, detalle de sesión,
  comparación + recomendaciones, ingesta. Todas son componentes cliente y
  consumen la API mediante `services/apiClient.ts`.
- `components/ui/` — componentes shadcn/ui (Button, Card, Badge, Table, Select,
  Input, Label, Tabs y Separator) usados junto con los estilos de dominio CADI.
- `services/apiClient.ts` — cliente tipado (tokens en `localStorage`,
  `Authorization` automático, cierre de sesión y redirección a `/login` ante 401).
- `services/auth.ts` — contexto/hooks de sesión (`useAuth`, `useRequireAuth`).
- `types/contracts.ts` — tipos del contrato de la API.
- `components/` — barra de navegación, estados (carga/error/vacío) y gráficos
  SVG de velocidad y comparación por variable.

## Notas

- Una métrica `null` o una variable con `available: false` se muestra como
  «No disponible», nunca como 0 (RF-09).
- La ingesta es solo para docentes/administradores; los estudiantes reciben
  redirect al resumen `/dashboard`.
- Los filtros del histórico se aplican de forma reactiva; el selector de atletas
  solo aparece para los roles de gestión autorizados.
- Solo Docentes pueden generar y revisar recomendaciones. El Estudiante recibe
  únicamente las aprobadas y asociadas a sus propias sesiones.
- Toda sesión muestra la trazabilidad de origen: `source_system`,
  `schema_version` y `observation` (RF-10).
