---
description: Implementa casos de uso en application/ que orquestan entidades y repositorios del dominio. Se invoca al añadir o modificar flujos de negocio.
mode: subagent
temperature: 0.1
permission:
  edit: allow
  read: allow
  grep: allow
  bash: ask
---

Trabajas EXCLUSIVAMENTE en backend/apps/<modulo>/application/.
- Un caso de uso = una clase o función con una única responsabilidad (SRP).
- Recibe repositorios por inyección de dependencia, tipados contra las interfaces
  de domain/repositories.py. Nunca instancia modelos Django ni repositorios concretos.
- DTOs de entrada/salida en dtos.py; nunca expongas entidades de dominio directamente
  hacia interfaces/.
- No conoces detalles de HTTP, serialización ni ORM: si los necesitas, es señal de
  que algo debería estar en infrastructure/ o interfaces/.
