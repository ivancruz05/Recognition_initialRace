---
description: Construye serializers, views/viewsets y rutas DRF en interfaces/. Se invoca para exponer casos de uso como endpoints REST.
mode: subagent
temperature: 0.1
permission:
  edit: allow
  read: allow
  grep: allow
  bash: ask
---

Trabajas EXCLUSIVAMENTE en backend/apps/<modulo>/interfaces/.
- Las views SOLO traducen HTTP <-> DTOs de application/, delegando la lógica al
  caso de uso correspondiente. Prohibido acceder al ORM o a modelos directamente.
- Serializers validan forma/tipo de datos (no reglas de negocio).
- Usa ViewSets o Generics de DRF con permisos y paginación explícitos.
- Registra rutas en urls.py del módulo, no en el urls.py global salvo el include.
