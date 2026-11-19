"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowUpRight, CalendarDays, GitCompareArrows, UserRound } from "lucide-react";

import { api, ApiError } from "@/services/apiClient";
import { isStaff, useRequireAuth } from "@/services/auth";
import type { Athlete, DashboardSummary, SessionDetail, SessionListItem, VariableName } from "@/types/contracts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorBox, Loading, VARIABLE_LABELS, errorMessage, formatDate, formatValue } from "@/components/ui";
import { SeriesChart } from "@/components/SeriesChart";

const VARIABLES: VariableName[] = ["posture", "speed", "stride", "cadence"];
const UNITS: Partial<Record<VariableName, string>> = {
  speed: "m/s",
  stride: "m",
  cadence: "pasos/s",
};
const MAX_COMPARE = 4;

export default function AthleteDetailPage() {
  const params = useParams<{ athlete_id: string }>();
  const athleteId = params.athlete_id;
  const { profile, ready } = useRequireAuth();
  const router = useRouter();

  const [athlete, setAthlete] = useState<Athlete | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [latestDetail, setLatestDetail] = useState<SessionDetail | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || profile === null) return;
    if (!isStaff(profile)) {
      router.replace("/dashboard");
      return;
    }

    let cancelled = false;
    setLoading(true);
    Promise.all([
      api.getAthlete(athleteId),
      api.dashboardSummary({ athlete_id: athleteId }),
      api.listSessions({ athlete_id: athleteId }),
    ])
      .then(([athleteData, summaryData, sessionRows]) => {
        if (cancelled) return;
        setAthlete(athleteData);
        setSummary(summaryData);
        setSessions(sessionRows);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof ApiError
              ? cause.detail
              : "No se pudo cargar la ficha seudonimizada del atleta.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ready, profile?.id, profile?.user_type, athleteId, router]);

  const latestSession = summary?.latest_session;
  useEffect(() => {
    const sessionId = latestSession?.session_id;
    if (!sessionId) {
      setLatestDetail(null);
      return;
    }
    let cancelled = false;
    api.getSession(sessionId)
      .then((detail) => {
        if (!cancelled) setLatestDetail(detail);
      })
      .catch(() => {
        if (!cancelled) setLatestDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [latestSession?.session_id]);

  const toggleSelected = (sessionId: string) => {
    setSelected((current) => {
      if (current.includes(sessionId)) return current.filter((id) => id !== sessionId);
      if (current.length >= MAX_COMPARE) return current;
      return [...current, sessionId];
    });
  };

  const compareSelected = () => {
    if (selected.length < 2) return;
    router.push(`/sessions/compare?ids=${encodeURIComponent(selected.join(","))}`);
  };

  const completeness = summary?.completeness;
  const averages = summary?.averages;
  const latestSpeed = useMemo(
    () => latestDetail?.variables.find((variable) => variable.name === "speed"),
    [latestDetail],
  );

  if (!ready || profile === null || loading) return <Loading text="Cargando ficha del atleta…" />;
  if (!isStaff(profile)) return <Loading text="Redirigiendo…" />;
  if (error || !athlete || !summary) {
    return <div className="container">{error ? <ErrorBox message={error} /> : <EmptyState>No se encontró el atleta.</EmptyState>}</div>;
  }

  return (
    <div className="container athlete-detail-page">
      <Link className="back-link" href="/athletes">
        <ArrowLeft size={16} aria-hidden="true" /> Volver al roster
      </Link>

      <section className="athlete-profile-hero">
        <div className="athlete-profile-main">
          <div className="athlete-code-mark" aria-hidden="true">
            <UserRound size={25} />
          </div>
          <div className="athlete-profile-copy">
            <p className="eyebrow">FICHA TÉCNICA · IDENTIFICADOR SEUDONIMIZADO</p>
            <h1>{athlete.athlete_id}</h1>
            <p>{athlete.label ?? "Sin alias autorizado"}</p>
            <div className="athlete-profile-tags">
              <Badge variant="secondary">{athlete.group ?? "Grupo no informado"}</Badge>
              <span><CalendarDays size={14} aria-hidden="true" /> Registrado {athlete.registered_at}</span>
              <span>{summary.total_sessions} sesiones</span>
            </div>
          </div>
        </div>
        <Link className="btn secondary" href={`/sessions?athlete_id=${encodeURIComponent(athlete.athlete_id)}`}>
          Ver pruebas <ArrowUpRight size={15} aria-hidden="true" />
        </Link>
      </section>

      <section className="athlete-variable-grid" aria-label="Resumen de variables">
        {VARIABLES.map((name) => (
          <Card className={`athlete-variable-card athlete-variable-${name}`} key={name}>
            <div className="athlete-variable-top">
              <span>{VARIABLE_LABELS[name]}</span>
              <span>{completeness?.[name] ?? 0}%</span>
            </div>
            <strong>
              {formatValue(averages?.[name], UNITS[name])}
            </strong>
            {name === "posture" && <small>Unidad conservada de la fuente</small>}
            <div className="completeness-track" role="progressbar" aria-label={`Completitud ${VARIABLE_LABELS[name]}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={completeness?.[name] ?? 0}>
              <span style={{ width: `${Math.max(0, Math.min(100, completeness?.[name] ?? 0))}%` }} />
            </div>
          </Card>
        ))}
      </section>

      <section className="athlete-history-layout">
        <div className="section-card-wrapper athlete-history-card">
          <div className="section-card-header">
            <div>
              <p className="eyebrow">HISTORIAL AUTORIZADO</p>
              <h2>Pruebas y sesiones</h2>
              <p className="small muted">Selecciona entre dos y {MAX_COMPARE} sesiones para compararlas.</p>
            </div>
            <div className="flex items-center gap-2 text-sm muted">
              <span>{sessions.length} registros</span>
              {selected.length > 0 && <Badge variant="secondary">{selected.length} seleccionadas</Badge>}
            </div>
          </div>
          {sessions.length === 0 ? (
            <div className="roster-empty"><EmptyState>Este atleta todavía no tiene sesiones registradas.</EmptyState></div>
          ) : (
            <div className="table-wrap">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12 text-center"><span className="sr-only">Comparar</span><GitCompareArrows className="w-4 h-4 mx-auto" aria-hidden="true" /></TableHead>
                    <TableHead>Sesión / origen</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Prueba</TableHead>
                    <TableHead>Variables disponibles</TableHead>
                    <TableHead className="text-right">Acción</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((session) => {
                    const isSelected = selected.includes(session.session_id);
                    return (
                      <TableRow key={session.session_id} data-state={isSelected ? "selected" : undefined}>
                        <TableCell className="text-center">
                          <input type="checkbox" aria-label={`Seleccionar ${session.session_id}`} checked={isSelected} disabled={!isSelected && selected.length >= MAX_COMPARE} onChange={() => toggleSelected(session.session_id)} />
                        </TableCell>
                        <TableCell>
                          <strong>{session.session_id}</strong>
                          <span className="table-subline">{session.source_system} · v{session.schema_version ?? "—"}</span>
                        </TableCell>
                        <TableCell className="whitespace-nowrap">{formatDate(session.timestamp)}</TableCell>
                        <TableCell>{session.test_type}</TableCell>
                        <TableCell>
                          {session.available_variables.length
                            ? session.available_variables.map((name) => VARIABLE_LABELS[name] ?? name).join(" · ")
                            : <span className="na">No disponible</span>}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link className="row-link" href={`/sessions/${encodeURIComponent(session.session_id)}`}>Detalle ↗</Link>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        <aside className="athlete-insight-column">
          <Card className="athlete-latest-card">
            <p className="eyebrow">SESIÓN MÁS RECIENTE</p>
            {latestSession ? (
              <>
                <h2>{latestSession.session_id}</h2>
                <p>{latestSession.test_type} · {formatDate(latestSession.timestamp)}</p>
                {latestSpeed?.available && latestSpeed.series?.length ? (
                  <SeriesChart series={latestSpeed.series} variable="speed" unit={latestSpeed.unit} />
                ) : (
                  <div className="notice-box athlete-no-series">Sin serie de velocidad disponible en la fuente.</div>
                )}
                <Link className="text-link" href={`/sessions/${encodeURIComponent(latestSession.session_id)}`}>Abrir detalle <ArrowUpRight size={14} aria-hidden="true" /></Link>
              </>
            ) : (
              <EmptyState>No hay sesión reciente.</EmptyState>
            )}
          </Card>

          {selected.length > 0 && (
            <Card className="athlete-compare-card">
              <div className="athlete-compare-number">{selected.length}</div>
              <div>
                <strong>Sesiones seleccionadas</strong>
                <p>El comparador permite hasta {MAX_COMPARE} registros.</p>
              </div>
              <div className="athlete-compare-actions">
                <Button variant="outline" onClick={() => setSelected([])}>Limpiar</Button>
                <Button className="btn" disabled={selected.length < 2} onClick={compareSelected}>Comparar</Button>
              </div>
            </Card>
          )}
        </aside>
      </section>
    </div>
  );
}
