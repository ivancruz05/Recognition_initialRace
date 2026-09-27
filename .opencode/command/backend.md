---
description: Orquesta una tarea del backend Django con Clean Architecture repartiéndola entre los subagentes por capa.
agent: orchestrator
---

Tarea a ejecutar: $ARGUMENTS

Coordina esta tarea siguiendo tu protocolo de orquestación:

1. Define alcance (módulo/archivos, capa que cambia, criterio de terminado) antes de despachar.
2. Delega en orden: `domain-architect` → `use-case-builder` → `infra-adapter` → `api-builder` → `test-engineer` → `architecture-reviewer`, pasando a cada uno el contexto explícito (módulo, entidad, campos, reglas de negocio).
3. Si la tarea toca una sola capa, invoca solo ese subagente + `test-engineer` + `architecture-reviewer`.
4. Si `architecture-reviewer` reporta una violación, corrige con el subagente correspondiente y vuelve a invocarlo antes de cerrar.
5. Consolida un único reporte: qué cambió por capa, `archivo:línea`, qué queda pendiente.
