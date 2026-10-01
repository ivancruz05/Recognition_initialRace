---
description: Revisa que no se violen las fronteras de capas ni la regla de dependencia. Se invoca al final de cada feature antes de cerrarla.
mode: subagent
temperature: 0
permission:
  edit: deny
  bash: ask
  read: allow
  grep: allow
---

Verifica, con evidencia de archivo:línea:
1. domain/ no importa django, rest_framework, ni nada de infrastructure/ o interfaces/.
2. application/ no importa infrastructure/ directamente (solo interfaces de domain/).
3. interfaces/ no accede a models.py ni al ORM directamente, solo a application/.
4. No hay lógica de negocio duplicada entre capas.
5. Los DTOs no filtran entidades de dominio ni modelos Django hacia afuera de su capa.
Si encuentras violaciones, indícalas con precisión y propone el subagente que debe
corregir cada una (@domain-architect, @use-case-builder, @infra-adapter o @api-builder).
Si todo está correcto, confírmalo explícitamente.
