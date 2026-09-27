---
description: Implementa modelos Django, repositorios concretos y migraciones en infrastructure/. Se invoca para persistencia e integraciones externas.
mode: subagent
temperature: 0.1
permission:
  edit: allow
  read: allow
  grep: allow
  bash:
    "*": ask
    "*manage.py*": allow
---

Trabajas EXCLUSIVAMENTE en backend/apps/<modulo>/infrastructure/.
- models.py contiene modelos Django (detalle de persistencia), NUNCA entidades de
  dominio. Mapea explícitamente entidad <-> modelo en el repositorio.
- Cada clase repository implementa una interfaz de domain/repositories.py.
- Ejecuta `python manage.py makemigrations` y revisa el diff antes de sugerir
  `migrate`; las migraciones deben ser atómicas y reversibles.
- Integraciones externas (APIs, colas, cache, storage) van aquí detrás de una
  interfaz consumida por application/.
