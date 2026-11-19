"use client";

import type { Averages, Completeness, VariableName } from "@/types/contracts";
import { Activity, Clock, Footprints, Zap } from "lucide-react";

interface BiomechanicsTelemetryGridProps {
  averages: Averages;
  completeness: Completeness;
}

const TELEMETRY_CONFIG: Record<
  VariableName,
  {
    label: string;
    unit: string;
    subtitle: string;
    benchmarkNote: string;
    className: string;
    Icon: React.ComponentType<{ className?: string }>;
  }
> = {
  posture: {
    label: "Indicador postural",
    unit: "",
    subtitle: "Valor informado por la fuente",
    benchmarkNote: "Se conserva sin recálculo ni interpretación adicional",
    className: "var-posture",
    Icon: Activity,
  },
  speed: {
    label: "Velocidad media",
    unit: "m/s",
    subtitle: "Desplazamiento horizontal",
    benchmarkNote: "Velocidad media de tramo de 10 m",
    className: "var-speed",
    Icon: Zap,
  },
  stride: {
    label: "Longitud de zancada",
    unit: "m",
    subtitle: "Amplitud media de paso",
    benchmarkNote: "Distancia media entre apoyos sucesivos",
    className: "var-stride",
    Icon: Footprints,
  },
  cadence: {
    label: "Cadencia de paso",
    unit: "pasos/s",
    subtitle: "Frecuencia de apoyos",
    benchmarkNote: "Frecuencia de ciclo de apoyo por segundo",
    className: "var-cadence",
    Icon: Clock,
  },
};

const VARIABLE_KEYS: VariableName[] = ["posture", "speed", "stride", "cadence"];

export function BiomechanicsTelemetryGrid({
  averages,
  completeness,
}: BiomechanicsTelemetryGridProps) {
  return (
    <section aria-labelledby="telemetry-grid-title" className="flex flex-col gap-3">
      <div className="flex justify-between items-baseline flex-wrap gap-2">
        <div>
          <h2 id="telemetry-grid-title" className="text-base font-bold text-navy">
            Variables Cinemáticas Clave
          </h2>
          <p className="text-xs text-muted-foreground">
            Promedios calculados exclusivamente sobre registros válidos (Norma RF-09: ausentes sin imputación a cero).
          </p>
        </div>
      </div>

      <div className="kpi-row-variables">
        {VARIABLE_KEYS.map((name) => {
          const config = TELEMETRY_CONFIG[name];
          const value = averages[name];
          const pct = completeness[name] ?? 0;
          const Icon = config.Icon;
          const isAvailable = value !== null && value !== undefined;

          return (
            <article
              key={name}
              className={`var-kpi-card ${config.className}`}
              aria-label={`${config.label}: ${isAvailable ? `${value} ${config.unit}` : "No disponible"}`}
            >
              <div>
                <div className="var-kpi-head">
                  <div className="var-kpi-title-block">
                    <h3 className="var-kpi-name">{config.label}</h3>
                    <span className="var-kpi-desc">{config.subtitle}</span>
                  </div>
                  <div className="var-kpi-icon-wrap" aria-hidden="true">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>

                <div className="var-kpi-body">
                  {isAvailable ? (
                    <div className="var-kpi-value">
                      {Number(value.toFixed(3))}
                      {config.unit && <span className="var-kpi-unit">{config.unit}</span>}
                    </div>
                  ) : (
                    <div className="na text-base font-normal py-1 text-muted-foreground">
                      No disponible
                    </div>
                  )}
                  <p className="text-[11px] text-muted-foreground/80 mt-1">
                    {config.benchmarkNote}
                  </p>
                </div>
              </div>

              <div className="var-kpi-foot">
                <div className="var-kpi-completeness-info">
                  <span>Completitud de captura</span>
                  <strong className="text-foreground font-mono">{pct}%</strong>
                </div>

                <div
                  className="completeness-track"
                  role="progressbar"
                  aria-label={`Completitud de ${config.label}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={pct}
                >
                  <span
                    style={{
                      width: `${Math.max(0, Math.min(100, pct))}%`,
                    }}
                  />
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
