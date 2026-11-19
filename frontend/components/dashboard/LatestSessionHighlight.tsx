"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { formatDate, VARIABLE_LABELS } from "@/components/ui";
import type { SessionListItem } from "@/types/contracts";
import { ArrowUpRight, Clock } from "lucide-react";

interface LatestSessionHighlightProps {
  latestSession: SessionListItem | null | undefined;
}

export function LatestSessionHighlight({
  latestSession,
}: LatestSessionHighlightProps) {
  if (!latestSession) return null;

  return (
    <section aria-labelledby="latest-session-title">
      <div className="latest-session-card">
        <div className="latest-session-top">
          <span className="latest-session-label">
            <Clock className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
            Última prueba procesada
          </span>
          <Badge
            variant="outline"
            className="border-white/20 text-white/90 text-xs font-mono"
          >
            {formatDate(latestSession.timestamp)}
          </Badge>
        </div>

        <div className="latest-session-content">
          <div>
            <div className="latest-session-item-k">Identificador de Sesión</div>
            <div className="latest-session-item-v font-mono text-lg">
              {latestSession.session_id}
            </div>
          </div>

          <div>
            <div className="latest-session-item-k">Atleta</div>
            <div className="latest-session-item-v font-mono">
              {latestSession.athlete_id}
            </div>
          </div>

          <div>
            <div className="latest-session-item-k">Tipo de Prueba</div>
            <div className="latest-session-item-v">{latestSession.test_type}</div>
          </div>

          <div>
            <div className="latest-session-item-k">Origen y Versión (RF-10)</div>
            <div className="latest-session-item-v text-sm font-normal text-slate-200">
              {latestSession.source_system} · v{latestSession.schema_version ?? "No disponible"}
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-3 border-t border-white/10">
          <div>
            <span className="latest-session-item-k block mb-1">
              Variables cinemáticas procesadas:
            </span>
            <div className="latest-session-pills">
              {latestSession.available_variables.length > 0 ? (
                latestSession.available_variables.map((varName) => (
                  <span key={varName} className="latest-pill">
                    {VARIABLE_LABELS[varName] ?? varName}
                  </span>
                ))
              ) : (
                <span className="na text-xs text-white/60">
                  Sin variables disponibles
                </span>
              )}
            </div>
          </div>

          <Link
            href={`/sessions/${encodeURIComponent(latestSession.session_id)}`}
            className="btn secondary text-xs sm:text-sm shrink-0"
          >
            Ver detalle de sesión <ArrowUpRight className="w-3.5 h-3.5 ml-1 inline" />
          </Link>
        </div>
      </div>
    </section>
  );
}
