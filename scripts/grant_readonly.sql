-- Permisos de lectura para el usuario de dashboard (Athletic Analysis).
-- Ejecutar como dueño de las tablas / rol con privilegios (el mismo que corre las migraciones,
-- p. ej. neondb_owner), NO como dashboard_ro.
--
-- Uso:
--   psql "postgresql://<owner>:<pass>@ep-flat-math-arssn337-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require" \
--        -f scripts/grant_readonly.sql

-- 1. Tablas existentes (las 12 de public).
GRANT USAGE ON SCHEMA public TO dashboard_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard_ro;

-- 2. Tablas futuras creadas por el rol que ejecuta este script (p. ej. nuevas migraciones).
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dashboard_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO dashboard_ro;

-- 3. Verificación: debe devolver 12 filas con select_ok = t.
SELECT c.relname AS tabla,
       has_table_privilege('dashboard_ro', c.oid, 'SELECT') AS select_ok
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
ORDER BY 1;

-- 4. (Opcional) Bloqueo explícito de escritura, para que el "solo lectura" sea real
--    y no dependa únicamente de que nadie haga un GRANT de más.
-- REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM dashboard_ro;
