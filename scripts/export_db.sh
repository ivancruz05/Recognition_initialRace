#!/usr/bin/env bash
# Exporta (solo lectura) las tablas accesibles de la base Athletic Analysis
# a data_export/: schema.sql, csv/<tabla>.csv y manifest.json.
#
# Uso:
#   export DATABASE_URL="postgresql://usuario:clave@host/db?sslmode=require"
#   ./scripts/export_db.sh
#
# Nunca hardcodear credenciales en este archivo.

set -euo pipefail

: "${DATABASE_URL:?Define DATABASE_URL antes de ejecutar (postgresql://user:pass@host/db?sslmode=require)}"

OUT_DIR="${OUT_DIR:-data_export}"
TABLES=(${TABLES:-analyses athletes frame_metrics metrics tests videos})
# pg_dump debe ser >= version del servidor (Neon usa PG 18).
if [ -z "${PG_DUMP:-}" ]; then
  for candidate in /opt/homebrew/opt/libpq/bin/pg_dump "$(command -v pg_dump)"; do
    [ -x "$candidate" ] && PG_DUMP="$candidate" && break
  done
fi
PSQL="${PSQL:-$(command -v psql)}"

mkdir -p "$OUT_DIR/csv"

dump_args=()
for t in "${TABLES[@]}"; do dump_args+=(-t "public.$t"); done

echo "[1/3] Esquema -> $OUT_DIR/schema.sql"
"$PG_DUMP" "$DATABASE_URL" --no-owner --no-privileges --schema-only "${dump_args[@]}" -f "$OUT_DIR/schema.sql"

echo "[2/3] Datos -> $OUT_DIR/csv/*.csv"
for t in "${TABLES[@]}"; do
  "$PSQL" "$DATABASE_URL" -q -c "\copy (select * from public.$t order by id) to '$OUT_DIR/csv/$t.csv' csv header"
  printf '  %-16s %s filas\n' "$t" "$(( $(wc -l < "$OUT_DIR/csv/$t.csv") - 1 ))"
done

echo "[3/3] Manifest -> $OUT_DIR/manifest.json"
{
  echo "{"
  echo "  \"exported_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"server_version\": \"$("$PSQL" "$DATABASE_URL" -At -c 'show server_version')\","
  echo "  \"tables\": {"
  first=1
  for t in "${TABLES[@]}"; do
    [ $first -eq 1 ] || echo ","
    first=0
    rows=$(( $(wc -l < "$OUT_DIR/csv/$t.csv") - 1 ))
    bytes=$(wc -c < "$OUT_DIR/csv/$t.csv" | tr -d ' ')
    printf '    "%s": {"rows": %d, "csv_bytes": %d}' "$t" "$rows" "$bytes"
  done
  echo ""
  echo "  }"
  echo "}"
} > "$OUT_DIR/manifest.json"

echo "Listo. Archivos en $OUT_DIR/"
