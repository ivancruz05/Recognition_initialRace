# Datos locales

Este árbol organiza los datos de captura y análisis locales. Los archivos fuente
pueden contener información personal o imágenes identificables: no subir PII ni
videos al repositorio.

```text
src/data/
├── raw/
│   └── videos/
│       ├── mov/       # Videos MOV originales usados como entrada
│       └── mp4/       # Videos MP4 originales de capturas en vivo
├── processed/
│   └── csv/
│       ├── live/      # CSV generados durante capturas en vivo
│       ├── analysis/  # CSV generados al analizar archivos de video
│       └── legacy/    # Resultados heredados sin sesión asociada
└── metadata/
    └── manifests/     # Manifiestos JSON de las sesiones
```

Los datos `raw` son videos fuente y deben conservarse sin alterar. `processed`
contiene resultados CSV derivados; `legacy` separa resultados anteriores del
flujo por sesión. `manifests` registra el estado y los metadatos de cada sesión:
relaciona entradas y outputs por basename y session ID. Un estado `complete`
indica que finalizaron las salidas técnicas; no implica validación biomecánica.

Los archivos de datos sensibles se excluyen de Git mediante `.gitignore`. Los
`.gitkeep` solo preservan las carpetas vacías en el repositorio.
