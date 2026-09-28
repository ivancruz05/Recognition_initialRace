# Documentación del proyecto

Esta carpeta reúne la explicación técnica y académica del proyecto: su alcance, arquitectura, implementación y decisiones. Está pensada para apoyar la memoria y la sustentación del proyecto de grado.

## Índice

0. [Base académica del anteproyecto](00-base-anteproyecto.md)
1. [Contexto, objetivo y alcance](01-contexto-y-alcance.md)
2. [Arquitectura](02-arquitectura.md)
3. [Estructura del backend](03-estructura-backend.md)
4. [Flujos y dependencia de datos](04-flujos-y-dependencia-de-datos.md)
5. [Interfaz visual y estado del proyecto](05-interfaz-visual-y-estado.md)
6. [Modelo de datos y diagramas](06-modelado-y-diagramas.md)
7. [Requisitos, trazabilidad y datos](07-requisitos-y-trazabilidad.md)

## Convención de estado

- **Implementado:** se encuentra en el código actual.
- **Parcial:** existe una primera implementación, pero faltan partes del flujo.
- **Pendiente:** todavía no aparece implementado en este repositorio.
- **Dependiente de datos:** su definición o validación requiere los datos y especificaciones que suministre el proyecto.

La documentación distingue el estado actual de las propuestas futuras. Se debe actualizar cuando cambien el alcance, los datos disponibles o la implementación.

Los diagramas se mantienen en Mermaid dentro de Markdown para que puedan revisarse junto con el código. Los diagramas actuales reflejan únicamente lo implementado; los flujos analíticos todavía no implementados se marcan como propuestos.

## Punto de partida técnico

El repositorio actual contiene un backend Django en `backend/`. No se encontraron carpetas ni archivos de frontend (HTML, CSS, JavaScript, TypeScript o equivalentes) en el checkout inspeccionado. Por ello, la interfaz visual se documenta como trabajo por desarrollar, no como funcionalidad ya entregada.
