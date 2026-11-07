"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/services/apiClient";
import { useRequireAuth } from "@/services/auth";
import type {
  DashboardSummary,
  SessionListItem,
  VariableName,
} from "@/types/contracts";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  EmptyState,
  ErrorBox,
  KNOWN_UNITS,
  Loading,
  VARIABLE_LABELS,
  errorMessage,
  formatDate,
} from "@/components/ui";

const VARIABLE_ORDER: VariableName[] = ["posture", "speed", "stride", "cadence"];

export default function DashboardPage() {
  const { profile, ready } = useRequireAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentSessions, setRecentSessions] = useState<SessionListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready || profile === null) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([api.dashboardSummary(), api.listSessions()])
      .then(([data, sessions]) => {
        if (!cancelled) {
          setSummary(data);
          setRecentSessions(sessions.slice(0, 6));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ready, profile]);

  if (!ready || profile === null) return <Loading />;
  if (loading) return <Loading text="Cargando resumen…" />;
  if (error !== null) return <div className="container"><ErrorBox message={error} /></div>;
  if (summary === null) {
    return (
      <div className="container">
        <EmptyState>No hay datos de resumen disponibles.</EmptyState>
      </div>
    );
  }

  const averages: Partial<typeof summary.averages> = summary.averages ?? {};
  const completeness: Partial<typeof summary.completeness> =
    summary.completeness ?? {};
  const scopeLabel =
    summary.scope === "all"
      ? "Todos los atletas"
      : profile.user_type === "student"
        ? "Tu historial autorizado"
        : summary.scope.replace("athlete:", "Atleta ");

  return (
    <div className="container dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">CENTRO ACADÉMICO DEPORTIVO · FASE II</p>
          <h1 className="page-title">Resumen de pruebas</h1>
          <p className="page-subtitle">
            Historial disponible para <strong>{scopeLabel}</strong>
          </p>
        </div>
        <Link className="btn" href="/sessions">
          Explorar sesiones <span aria-hidden="true">↗</span>
        </Link>
      </div>

      <div className="grid grid-4">
        <Card className="card kpi-card kpi-primary">
          <div className="kpi-label">Sesiones registradas</div>
          <div className="kpi-value">{summary.total_sessions}</div>
          <div className="kpi-note">pruebas de velocidad en el histórico</div>
        </Card>
        <Card className="card kpi-card">
          <div className="kpi-label">Atletas evaluados</div>
          <div className="kpi-value">{summary.total_athletes}</div>
          <div className="kpi-note">códigos técnicos seudonimizados</div>
        </Card>
        {VARIABLE_ORDER.map((name) => {
          const unit = KNOWN_UNITS[name];
          const value = averages[name];
          const pct = completeness[name];
          return (
            <Card className={`card kpi-card kpi-${name}`} key={name}>
              <div className="kpi-label">Promedio · {VARIABLE_LABELS[name]}</div>
              <div className="kpi-value">
                {value === null || value === undefined ? (
                  <span className="na" style={{ fontSize: 18 }}>
                    No disponible
                  </span>
                ) : (
                  <>
                    {Number(value.toFixed(3))}
                    {unit !== undefined && <span className="kpi-unit">{unit}</span>}
                  </>
                )}
              </div>
              <div className="kpi-note">
                {pct === null || pct === undefined
                  ? "Completitud no disponible"
                  : `Completitud ${pct}%`}
              </div>
              {pct !== null && pct !== undefined && (
                <div
                  className="completeness-track"
                  role="progressbar"
                  aria-label={`Completitud de ${VARIABLE_LABELS[name]}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={pct}
                >
                  <span style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <section className="card recent-card" aria-labelledby="recent-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">HISTÓRICO</p>
            <h2 id="recent-title">Sesiones recientes</h2>
          </div>
          <Link href="/sessions" className="text-link">Ver todas <span aria-hidden="true">→</span></Link>
        </div>
        {recentSessions.length === 0 ? (
          <EmptyState>Todavía no hay sesiones registradas.</EmptyState>
        ) : (
          <div className="table-wrap">
              <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sesión / fuente</TableHead>
                  <TableHead>Atleta</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Prueba</TableHead>
                  <TableHead>Variables disponibles</TableHead>
                  <TableHead><span className="sr-only">Acciones</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentSessions.map((session) => (
                  <TableRow key={session.session_id}>
                    <TableCell>
                      <strong>{session.session_id}</strong>
                      <span className="table-subline">{session.source_system} · v{session.schema_version ?? "—"}</span>
                    </TableCell>
                    <TableCell>{session.athlete_id}</TableCell>
                    <TableCell>{formatDate(session.timestamp)}</TableCell>
                    <TableCell>{session.test_type}</TableCell>
                    <TableCell>
                      {session.available_variables.length
                        ? session.available_variables.map((name) => VARIABLE_LABELS[name] ?? name).join(" · ")
                        : <span className="na">No disponible</span>}
                    </TableCell>
                    <TableCell>
                      <Link className="row-link" href={`/sessions/${encodeURIComponent(session.session_id)}`} aria-label={`Abrir sesión ${session.session_id}`}>Abrir <span aria-hidden="true">↗</span></Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
              </Table>
          </div>
        )}
      </section>
    </div>
  );
}
