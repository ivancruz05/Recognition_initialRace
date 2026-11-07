"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/services/apiClient";
import { useRequireAuth } from "@/services/auth";
import type { SessionDetail, Variable } from "@/types/contracts";
import {
  EmptyState,
  ErrorBox,
  Loading,
  VARIABLE_LABELS,
  ValueOrNA,
  errorMessage,
  formatDate,
} from "@/components/ui";
import { SeriesChart } from "@/components/SeriesChart";
import { Badge } from "@/components/ui/badge";

function VariableCard({ variable }: { variable: Variable }) {
  const label = VARIABLE_LABELS[variable.name] ?? variable.name;

  return (
    <div className="card var-card">
      <h3>
        {label}
        {!variable.available && <Badge variant="secondary" className="badge grey">No disponible</Badge>}
        {variable.available && (
          <Badge className="badge">{variable.unit || "s/u"}</Badge>
        )}
      </h3>

      {!variable.available ? (
        <p className="na" style={{ margin: 0 }}>
          No disponible en esta sesión.
        </p>
      ) : (
        <>
          <div className="metric-row">
            <div className="metric">
              <div className="k">Valor</div>
              <div className="v">
                <ValueOrNA value={variable.value} unit={variable.unit} />
              </div>
            </div>
            {variable.peak !== undefined && variable.peak !== null && (
              <div className="metric">
                <div className="k">Pico</div>
                <div className="v">
                  <ValueOrNA value={variable.peak} unit={variable.unit} />
                </div>
              </div>
            )}
          </div>

          {variable.parameter !== undefined && variable.parameter !== null && (
            <p className="small muted" style={{ marginBottom: 4 }}>
              Parámetro: <strong>{variable.parameter}</strong>
            </p>
          )}

          {variable.details !== undefined && variable.details.length > 0 && (
            <ul className="evidence">
              {variable.details.map((detail) => (
                <li key={detail.name}>
                  {detail.name}:{" "}
                  <ValueOrNA value={detail.value} />
                </li>
              ))}
            </ul>
          )}

          {variable.series !== undefined && variable.series.length > 0 && (
            <SeriesChart series={variable.series} variable={variable.name} unit={variable.unit} />
          )}
        </>
      )}
    </div>
  );
}

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const { profile, ready } = useRequireAuth();

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || profile === null || !sessionId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getSession(sessionId)
      .then((data) => {
        if (!cancelled) setSession(data);
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
  }, [ready, profile, sessionId]);

  if (!ready || profile === null) return <Loading />;

  return (
    <div className="container detail-page">

      {loading && <Loading text="Cargando sesión…" />}

      {error !== null && <ErrorBox message={error} />}

      {!loading && error === null && session === null && (
        <EmptyState>No se encontró la sesión.</EmptyState>
      )}

      {session !== null && (
        <>
          <div className="page-heading detail-heading">
            <div>
              <p className="eyebrow">SESIÓN DE VELOCIDAD · HISTÓRICO CADI</p>
              <h1 className="page-title">{session.session_id}</h1>
              <div className="detail-title-meta">
                <span>Atleta <strong>{session.athlete_id}</strong></span>
                <span>{formatDate(session.timestamp)}</span>
                <Badge className="badge">{session.test_type}</Badge>
                <Badge variant="secondary" className="badge grey">
                  {session.variables.filter((variable) => variable.available).length}/4 variables disponibles
                </Badge>
              </div>
            </div>
            <Link href="/sessions" className="btn secondary detail-back-link">
              ← Volver al histórico
            </Link>
          </div>

          <div className="card source-card">
            <p className="eyebrow">RF-10 · PROCEDENCIA</p>
            <h2>Origen del registro</h2>
            <div className="source-block">
              <div>
                <div className="k">Sistema de origen</div>
                <div className="v">{session.source.source_system}</div>
              </div>
              <div>
                <div className="k">Versión de esquema</div>
                  <div className="v">{session.source.schema_version ?? "No disponible"}</div>
              </div>
              <div>
                <div className="k">Observación</div>
                <div className="v">
                  {session.source.observation
                    ? session.source.observation
                    : "Sin observaciones."}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-2 detail-variable-grid">
            {session.variables.map((variable) => (
              <VariableCard key={variable.name} variable={variable} />
            ))}
          </div>

          <div className="notice-box">
            Los valores no disponibles se muestran como «No disponible»: nunca se
            sustituyen por 0 (RF-09).
          </div>
        </>
      )}
    </div>
  );
}
