# Trazabilidad de CADI Fase II

Esta matriz relaciona los requisitos de la monografía con el código y las
pruebas automatizadas. «Implementado» describe el comportamiento del software;
no equivale a evidencia de validación empírica o de uso en producción.

## Requisitos funcionales

| Requisito | Implementación | Verificación |
|---|---|---|
| RF-01 — ingesta y consulta con contrato versionado | `backend/apps/sessions/domain/contract.py`; `application/use_cases.py:IngestSessionContract`; `infrastructure/file_ingest/fase1_csv_adapter.py`; `management/commands/import_fase1_export.py` | `sessions/tests/test_domain.py`, `test_contract_validator.py`, `test_application.py`, `test_fase1_adapter.py`, `test_api.py` |
| RF-02 — JWT y roles | `backend/apps/accounts/infrastructure/jwt.py`; `interfaces/permissions.py`; RBAC de sesiones en `backend/apps/sessions/application/use_cases.py` | suites `backend/apps/accounts/test/`, `backend/apps/sessions/tests/test_api.py` |
| RF-03 — dashboard | `GetDashboardSummary` y `DashboardSummaryView` | `sessions/tests/test_application.py`, `test_api.py` |
| RF-04 — filtros por atleta, sesión y fecha | `SessionFilterInput`, `SessionFilters`, `ListSessionsByFilter` | `sessions/tests/test_application.py`; filtro HTTP parcial en `test_api.py` |
| RF-05…RF-08 — variables y comparación | `SessionDetailDTO`, `ComparisonMatrixDTO`, `SessionDetailSerializer`, `ComparisonSerializer`; UI en `frontend/app/sessions/[id]/page.tsx` y `frontend/app/sessions/compare/page.tsx` | `sessions/tests/test_domain.py`, `test_api.py`; build de Next.js |
| RF-09 — ausentes sin convertir a cero | estados `AVAILABLE`/`NOT_AVAILABLE` en `sessions/domain/entities.py`; columnas nullable en ORM; UI muestra «No disponible» | `sessions/tests/test_domain.py`, `test_application.py`, `test_contract_validator.py`, `test_api.py`; comprobación UI manual pendiente |
| RF-10 — procedencia y trazabilidad | contrato, `metadata`, DTOs de sesión y `metadata.observation` del adaptador Fase I | `sessions/tests/test_domain.py`, `test_fase1_adapter.py`, `test_api.py` |
| RF-11 — analítica descriptiva | `backend/apps/analytics/application/use_cases.py:GetAnalytics` | `analytics/tests/test_application.py`, `test_api.py` |
| RF-12 — componente predictivo | **Pendiente**: no hay modelo predictivo ni estimación. El puerto actual desacopla recomendaciones basadas en reglas; la respuesta declara `model_version: null` y `PENDING_EVIDENCE`. | `analytics/tests/test_application.py`, `test_api.py` verifican que la limitación se exponga sin alegar exactitud |
| RF-13…RF-14 — recomendaciones documentadas y trazables | reglas R-00…R-05 en `backend/apps/analytics/infrastructure/rule_based_recommendations.py`; `cadi_recommendation` conserva evidencia, sesiones de origen, versiones, estado, docente responsable, fecha y nota de revisión. Solo una recomendación aprobada aparece al Estudiante y solo para sus sesiones. | `analytics/tests/test_rules.py`, `test_application.py`, `test_api.py` |

## Historias y casos de uso

| Elemento | Código principal | Estado |
|---|---|---|
| HU-01 / CU-01 dashboard | `sessions/application/use_cases.py:GetDashboardSummary`; `GET /api/v1/dashboard/summary/` | Implementado; no se ha medido el objetivo de latencia de 2 s (RNF-05). |
| HU-02 / CU-02 consulta y filtros | `ListSessionsByFilter`; `GET /api/v1/sessions/` | Implementado en API; falta una verificación de interacción reactiva en navegador. |
| HU-03…HU-06 / CU-03 detalle y CU-04 comparación | `GetSessionDetail`, `CompareSessions`; `/sessions/[id]` y `/sessions/compare` | Vistas con componentes shadcn/ui y gráficas SVG de velocidad/comparación. No se afirma haber realizado validación manual en todos los navegadores. |
| HU-07 / CU-05 desacople e ingesta | puertos de `sessions/domain`; adaptadores ORM, JSON, CSV e in-memory; `IngestSessionContract` | Implementado; lote inválido no persiste registros. |

## Requisitos no funcionales y evidencia pendiente

- **RNF-01, RNF-08:** dominio/aplicación se prueban sin ORM en los tests de casos de uso con `InMemorySessionRepository`.
- **RNF-03:** los errores de contrato se devuelven de forma estructurada; el registro técnico persistente de eventos requiere definir política de logging y retención.
- **RNF-04:** JWT, hash de contraseña y permisos por rol están implementados. La revisión de seguridad de despliegue/secretos queda fuera de estas pruebas.
- **RNF-05:** no se adjunta benchmark de rendimiento; el umbral de 2 s no se declara verificado.
- **RNF-06:** hay estilos responsivos básicos; la matriz de navegadores/tabletas requiere prueba manual.
- **RNF-07:** respuestas de sesión y recomendaciones mantienen sus IDs de origen; la prueba visual de cada punto de gráfico queda pendiente.
- **RNF-09 / CP-08:** el comando `python manage.py import_fase1_export` genera un perfil reproducible en `data_export/perfil_calidad_fase1.json`. `data_export/` se mantiene local e ignorado por privacidad; el perfil no se versiona.
- **RNF-10 / CP-10…CP-12:** reglas descriptivas, insuficiencia de datos, aprobación/rechazo, rechazo de segundas decisiones y aislamiento por rol están probados. La validación de lenguaje, consentimiento institucional y evidencia de uso real siguen pendientes.
- **HU-08 / HU-09:** implementados `POST /analytics/recommendations/generate/`, `POST /analytics/recommendations/{id}/review/` y `GET /analytics/recommendations/?ids=...`. Docentes generan y aprueban/rechazan; Estudiantes reciben solo salidas aprobadas vinculadas a sus sesiones. `cadi_recommendation` conserva la decisión, quién revisó, cuándo y una nota opcional. El protocolo institucional de consentimiento informado debe definirse antes del despliegue con usuarios reales.
- **RNF-11 / CP-09:** no se reportan métricas predictivas. No se ha definido una variable objetivo validada, partición por atleta, baseline ni modelo empírico; por tanto, la evaluación queda pendiente.

## Ejecución reproducible

Desde la raíz del repositorio:

```bash
.venv/bin/pytest -q
```

Verificaciones adicionales:

```bash
cd backend && ../.venv/bin/python manage.py check
cd backend && ../.venv/bin/python manage.py makemigrations --check --dry-run
cd frontend && npm run build
```
