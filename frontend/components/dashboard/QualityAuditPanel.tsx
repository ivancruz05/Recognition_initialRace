"use client";

import { Badge } from "@/components/ui/badge";
import type { Completeness, VariableName } from "@/types/contracts";

interface QualityAuditPanelProps {
  completeness: Completeness;
}

const VARIABLES: { key: VariableName; label: string }[] = [
  { key: "posture", label: "Indicador postural" },
  { key: "speed", label: "Velocidad media" },
  { key: "stride", label: "Longitud de zancada" },
  { key: "cadence", label: "Cadencia de paso" },
];

export function QualityAuditPanel({ completeness }: QualityAuditPanelProps) {
  return (
    <section className="quality-card" aria-labelledby="quality-title">
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div>
          <h2 id="quality-title" className="text-base font-bold text-navy">
            Auditoría de Calidad e Integridad de Muestra
          </h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl leading-relaxed">
            Conforme a los requisitos de la monografía CADI Fase II, toda captura preserva
            la trazabilidad al contrato JSON original (RF-10). Los registros con datos no capturados
            se conservan como <em>No disponible</em>, evitando sesgar los promedios del atleta con ceros arbitrarios (RF-09).
          </p>
        </div>
        <Badge variant="outline" className="text-xs font-mono">
          Contrato versionado · CADI
        </Badge>
      </div>

      <div className="quality-grid mt-4">
        {VARIABLES.map(({ key, label }) => {
          const pct = completeness[key] ?? 0;
          return (
            <div key={key} className="quality-item">
              <div className="quality-item-head">
                <span className="text-xs font-medium text-navy">{label}</span>
                <span className="font-mono text-xs font-bold text-slate-800">{pct}%</span>
              </div>
              <div
                className="completeness-track"
                style={{ marginTop: 4, height: 6 }}
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={pct}
                aria-label={`Completitud de ${label}`}
              >
                <span style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
              </div>
              <div className="quality-note flex justify-between items-center text-[11px] mt-2">
                <span className="text-muted-foreground">Sesiones con dato:</span>
                <span className="font-semibold text-navy">{pct}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
