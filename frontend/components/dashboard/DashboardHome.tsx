"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Activity, ArrowUpRight } from "lucide-react";

import { api } from "@/services/apiClient";
import { useRequireAuth } from "@/services/auth";
import type { SessionDetail } from "@/types/contracts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorBox, Loading, formatValue } from "@/components/ui";
import { SeriesChart } from "@/components/SeriesChart";
import { ComparisonFloatingBar } from "./ComparisonFloatingBar";
import { DashboardFilters } from "./DashboardFilters";
import { DashboardHero } from "./DashboardHero";
import { LatestSessionHighlight } from "./LatestSessionHighlight";
import { QualityAuditPanel } from "./QualityAuditPanel";
import { RecentSessionsTable } from "./RecentSessionsTable";
import { BiomechanicsTelemetryGrid } from "./BiomechanicsTelemetryGrid";
import { useDashboardData } from "@/hooks/useDashboardData";

const MAX_COMPARE = 4;

export function DashboardHome() {
  const { profile, ready } = useRequireAuth();
  const router = useRouter();
  const dashboard = useDashboardData(profile, ready);
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [latestDetail, setLatestDetail] = useState<SessionDetail | null>(null);
  const [latestDetailLoading, setLatestDetailLoading] = useState(false);

  const latestSession = dashboard.summary?.latest_session;

  useEffect(() => {
    const sessionId = latestSession?.session_id;
    if (!sessionId) {
      setLatestDetail(null);
      setLatestDetailLoading(false);
      return;
    }

    let cancelled = false;
    setLatestDetailLoading(true);
    api.getSession(sessionId)
      .then((detail) => {
        if (!cancelled) setLatestDetail(detail);
      })
      .catch(() => {
        if (!cancelled) setLatestDetail(null);
      })
      .finally(() => {
        if (!cancelled) setLatestDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [latestSession?.session_id]);

  if (!ready || profile === null || dashboard.initialLoading) {
    return <Loading text="Cargando panel de resumen…" />;
  }

  const summary = dashboard.summary;
  const scopeLabel =
    summary?.scope === "all"
      ? "Todos los atletas"
      : profile.user_type === "student"
        ? `Atleta autorizado (${profile.athlete_id || "vínculo pendiente"})`
        : summary?.scope.replace("athlete:", "Atleta ") ?? "Alcance activo";
  const latestSpeed = latestDetail?.variables.find((variable) => variable.name === "speed");

  const toggleSession = (sessionId: string) => {
    setSelectedSessions((current) => {
      if (current.includes(sessionId)) return current.filter((id) => id !== sessionId);
      if (current.length >= MAX_COMPARE) return current;
      return [...current, sessionId];
    });
  };

  const compareSelected = () => {
    if (selectedSessions.length < 2) return;
    router.push(`/sessions/compare?ids=${encodeURIComponent(selectedSessions.join(","))}`);
  };

  return (
    <div className="container dashboard-v2">
      <DashboardHero
        profile={profile}
        scopeLabel={scopeLabel}
        isRefreshing={dashboard.isRefreshing}
        totalSessions={summary?.total_sessions ?? 0}
      />

      {dashboard.athletesError && (
        <ErrorBox message={`No se pudo cargar el catálogo de atletas: ${dashboard.athletesError}`} />
      )}
      {dashboard.error && <ErrorBox message={dashboard.error} />}

      <DashboardFilters
        filters={dashboard.filters}
        athletes={dashboard.athletes}
        profile={profile}
        activeFiltersCount={dashboard.activeFiltersCount}
        onFilterChange={dashboard.handleFilterChange}
        onClearFilters={() => {
          dashboard.handleClearFilters();
          setSelectedSessions([]);
        }}
      />

      <section aria-label="Indicadores del alcance consultado">
        <div className="kpi-row-overview">
          <Card className="kpi-card kpi-primary">
            <div className="flex justify-between items-start">
              <div>
                <div className="kpi-label">Sesiones registradas</div>
                <div className="kpi-value">{summary?.total_sessions ?? 0}</div>
                <div className="kpi-note">pruebas disponibles en el alcance actual</div>
              </div>
              <Activity className="w-8 h-8 opacity-40 text-white" aria-hidden="true" />
            </div>
          </Card>
          <Card className="kpi-card">
            <div className="flex justify-between items-start">
              <div>
                <div className="kpi-label">Atletas evaluados</div>
                <div className="kpi-value">{summary?.total_athletes ?? 0}</div>
                <div className="kpi-note">identificados mediante código seudonimizado</div>
              </div>
              <Activity className="w-8 h-8 text-primary opacity-60" aria-hidden="true" />
            </div>
          </Card>
        </div>
      </section>

      {summary?.total_sessions === 0 && (
        <section className="dashboard-empty-panel" aria-labelledby="empty-dashboard-title">
          <div className="dashboard-empty-track" aria-hidden="true"><span /><span /><span /></div>
          <div className="dashboard-empty-copy">
            <p className="eyebrow">HISTÓRICO LISTO PARA RECIBIR DATOS</p>
            <h2 id="empty-dashboard-title">Todavía no hay sesiones en este alcance</h2>
            <p>
              La Fase II consulta exportaciones estructuradas de pruebas; no captura video ni calcula mediciones primarias.
            </p>
            {profile.user_type === "teacher" || profile.user_type === "admin" ? (
              <Link className="btn" href="/ingest">Cargar exportación JSON <ArrowUpRight className="w-4 h-4 ml-1 inline" aria-hidden="true" /></Link>
            ) : (
              <p className="dashboard-empty-student-note">
                Pide a tu Docente que vincule tu código de atleta e importe tus sesiones.
              </p>
            )}
          </div>
        </section>
      )}

      <BiomechanicsTelemetryGrid
        averages={summary?.averages ?? { posture: null, speed: null, stride: null, cadence: null }}
        completeness={summary?.completeness ?? { posture: 0, speed: 0, stride: 0, cadence: 0 }}
      />

      <LatestSessionHighlight latestSession={latestSession} />

      {latestSession && (
        <Card className="dashboard-speed-card">
          <div className="dashboard-speed-header">
            <div>
              <p className="eyebrow">SERIE DE LA PRUEBA</p>
              <h2>Velocidad · {latestSession.session_id}</h2>
              <p>{latestSession.test_type}</p>
            </div>
            {latestSpeed?.available && (
              <Badge variant="secondary" className="font-mono">{latestSpeed.unit}</Badge>
            )}
          </div>
          {latestDetailLoading ? (
            <Loading text="Cargando serie de velocidad…" />
          ) : latestSpeed?.available && latestSpeed.series?.length ? (
            <>
              <div className="dashboard-speed-values">
                <span>Promedio: <strong>{formatValue(latestSpeed.value, latestSpeed.unit)}</strong></span>
                {latestSpeed.peak !== null && latestSpeed.peak !== undefined && (
                  <span>Pico: <strong>{formatValue(latestSpeed.peak, latestSpeed.unit)}</strong></span>
                )}
              </div>
              <SeriesChart series={latestSpeed.series} variable="speed" unit={latestSpeed.unit} />
              <p className="small muted">
                Serie temporal de una sesión; no representa una tendencia entre semanas.
              </p>
            </>
          ) : (
            <EmptyState>
              La fuente no incluyó una serie temporal para esta sesión. El valor puntual se consulta en el detalle.
            </EmptyState>
          )}
        </Card>
      )}

      <RecentSessionsTable
        sessions={dashboard.recentSessions}
        selectedSessions={selectedSessions}
        maxCompare={MAX_COMPARE}
        onToggleSelect={toggleSession}
      />

      {summary && <QualityAuditPanel completeness={summary.completeness} />}

      <ComparisonFloatingBar
        selectedCount={selectedSessions.length}
        maxCompare={MAX_COMPARE}
        onClear={() => setSelectedSessions([])}
        onCompare={compareSelected}
      />
    </div>
  );
}
