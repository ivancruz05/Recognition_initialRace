import type { ReactNode } from "react";

/** Estado de carga reutilizable. */
export function Loading({ text = "Cargando…" }: { text?: string }) {
  return <div className="state">{text}</div>;
}

/** Caja de error con mensaje legible para el usuario. */
export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-box" role="alert">
      {message}
    </div>
  );
}

/** Estado vacío (sin resultados). */
export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state">{children}</div>;
}

/** Traduce un ApiError (u otro error) a texto mostrable. */
export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "Error inesperado.";
}

export const VARIABLE_LABELS: Record<string, string> = {
  posture: "Postura",
  speed: "Velocidad",
  stride: "Zancada",
  cadence: "Cadencia",
};

/** Unidades conocidas del dominio (las sesiones traen su propia unit). */
export const KNOWN_UNITS: Record<string, string> = {
  speed: "m/s",
  stride: "m",
  cadence: "pasos/s",
};

/**
 * Formatea un valor numérico. `null`/`undefined` → "No disponible"
 * (RF-09: nunca se muestra un 0 inventado).
 */
export function formatValue(
  value: number | null | undefined,
  unit?: string,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "No disponible";
  }
  const formatted = Number.isInteger(value)
    ? String(value)
    : String(Number(value.toFixed(3)));
  return unit ? `${formatted} ${unit}` : formatted;
}

/** Igual que formatValue pero devuelve JSX con la marca "No disponible". */
export function ValueOrNA({
  value,
  unit,
}: {
  value: number | null | undefined;
  unit?: string;
}): ReactNode {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="na">No disponible</span>;
  }
  return <>{formatValue(value, unit)}</>;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  });
}
