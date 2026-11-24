# Backend CADI

## PostgreSQL en Supabase

Django usa SQLite localmente. En despliegue, define `DATABASE_URL` como secreto
del servicio backend con la cadena **Session pooler** de Supabase y `sslmode=require`.
No guardes esa cadena ni la contraseña de la base en Git.

Después de configurar el secreto en el servidor Django:

```bash
python manage.py migrate
python manage.py loaddata apps/sessions/fixtures/supabase_synthetic_demo.json
```

El fixture se carga una sola vez en una base vacía y contiene únicamente los
datos sintéticos de demostración versionados en el proyecto.

Para ampliar un entorno de demostración local hasta 30 atletas con 10
evaluaciones de sprint por atleta, carga la expansión después del fixture base:

```bash
python manage.py loaddata apps/sessions/fixtures/synthetic_demo_expansion.json
```

La expansión es aditiva y sus mediciones están marcadas como sintéticas; no
representan evaluaciones reales.

El backend Django debe estar desplegado en un servicio accesible por HTTPS.
Configura allí `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` y
`CORS_ALLOWED_ORIGINS`. En Vercel, configura `NEXT_PUBLIC_API_URL` con la URL
del backend seguida de `/api/v1` y vuelve a desplegar el frontend.

Si Supabase requiere una conexión IPv4, usa la cadena Session pooler del panel
**Connect** (puerto `5432`). La configuración SSL se aplica automáticamente
cuando la URL no especifica otro `sslmode`.
