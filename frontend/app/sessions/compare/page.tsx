"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/services/apiClient";
import { useRequireAuth } from "@/services/auth";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  AnalyticsResult,
  Comparison,
  ReviewDecision,
} from "@/types/contracts";
import { Button } from "@/components/ui/button";
import {
  EmptyState,
  ErrorBox,
  Loading,
  VARIABLE_LABELS,
  errorMessage,
  formatDate,
  formatValue,
} from "@/components/ui";

function Delta({ value, unit }: { value: number | null; unit?: string }) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="na">No disponible</span>;
  }
  const formatted = Number(value.toFixed(3));
  const suffix = unit ? ` ${unit}` : "";
  return (
    <span style={{ fontWeight: 700, color: formatted >= 0 ? "#15803d" : "#b91c1c" }}>
      {formatted > 0 ? `+${formatted}` : formatted}
      {suffix}
    </span>
  );
}

function ComparisonBars({ comparison }: { comparison: Comparison }) {
  return (
    <div className="comparison-chart-grid">
      {comparison.variables.map((variable) => {
        const values = variable.points
          .filter((point) => point.available && point.value !== null)
          .map((point) => point.value as number);
        const max = Math.max(0, ...values) || 1;
        return (
          <Card className="comparison-chart card" key={variable.name}>
            <div className="comparison-chart-heading">
              <div>
                <p className="eyebrow">COMPARACIÓN</p>
                <h3>{VARIABLE_LABELS[variable.name] ?? variable.name}</h3>
              </div>
              <span className="unit-tag">{variable.unit || "Sin unidad"}</span>
            </div>
            <div className="comparison-bars">
              {comparison.sessions.map((session) => {
                const point = variable.points.find(
                  (item) => item.session_id === session.session_id,
                );
                const value = point?.value;
                const available = Boolean(point?.available) && value !== null;
                const width = available
                  ? Math.max(2, Math.min(100, ((value as number) / max) * 100))
                  : 0;
                return (
                  <div className="comparison-bar-row" key={session.session_id}>
                    <span className="comparison-bar-id">{session.session_id}</span>
                    {available ? (
                      <>
                        <div
                          className="comparison-bar-track"
                          role="img"
                          aria-label={`${session.session_id}: ${formatValue(value, variable.unit)}`}
                        >
                          <span style={{ width: `${width}%` }} />
                        </div>
                        <strong className="comparison-bar-value">
                          {formatValue(value, variable.unit)}
                        </strong>
                      </>
                    ) : (
                      <span className="na comparison-bar-missing">No disponible</span>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="comparison-delta">
              Variación (última − primera): <Delta value={variable.delta} unit={variable.unit} />
            </p>
          </Card>
        );
      })}
    </div>
  );
}

function CompareContent() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") ?? "";
  const ids = idsParam
    .split(",")
    .map((id) => id.trim())
    .filter((id) => id.length > 0);

  const { profile, ready } = useRequireAuth();
  const isTeacher = profile?.user_type === "teacher";
  const canViewRecommendations = isTeacher || profile?.user_type === "student";

  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsResult | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!ready || profile === null || ids.length < 2) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setComparisonError(null);
    setAnalyticsError(null);

    const analyticsRequest = canViewRecommendations
      ? api.recommendations(ids)
      : Promise.resolve(null);

    Promise.allSettled([api.compareSessions(ids), analyticsRequest]).then(
      ([compareResult, analyticsResult]) => {
      if (cancelled) return;
      if (compareResult.status === "fulfilled") {
        setComparison(compareResult.value);
      } else {
        setComparisonError(errorMessage(compareResult.reason));
      }
      if (analyticsResult.status === "fulfilled" && analyticsResult.value !== null) {
        setAnalytics(analyticsResult.value);
      } else if (analyticsResult.status === "rejected") {
        setAnalyticsError(errorMessage(analyticsResult.reason));
      }
      setLoading(false);
      },
    );

    return () => {
      cancelled = true;
    };
  }, [ready, profile?.id, canViewRecommendations, idsParam]); // eslint-disable-line react-hooks/exhaustive-deps

  const generateRecommendations = async () => {
    setGenerating(true);
    setAnalyticsError(null);
    try {
      setAnalytics(await api.generateRecommendations(ids));
    } catch (error: unknown) {
      setAnalyticsError(errorMessage(error));
    } finally {
      setGenerating(false);
    }
  };

  const reviewRecommendation = async (
    recommendationId: string,
    decision: ReviewDecision,
  ) => {
    setReviewingId(recommendationId);
    setAnalyticsError(null);
    try {
      await api.reviewRecommendation(
        recommendationId,
        decision,
        reviewNotes[recommendationId],
      );
      setAnalytics(await api.recommendations(ids));
    } catch (error: unknown) {
      setAnalyticsError(errorMessage(error));
    } finally {
      setReviewingId(null);
    }
  };

  if (!ready || profile === null) return <Loading />;

  if (ids.length < 2) {
    return (
      <div className="container">
        <h1 className="page-title">Comparación de sesiones</h1>
        <EmptyState>
          Selecciona al menos dos sesiones en la{" "}
          <Link href="/sessions">página de sesiones</Link> para compararlas.
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="container">
      <p style={{ marginTop: 0 }}>
        <Link href="/sessions">← Volver a sesiones</Link>
      </p>
      <p className="eyebrow">ANÁLISIS HISTÓRICO</p>
      <h1 className="page-title">Comparación de sesiones</h1>
      <p className="page-subtitle">{ids.join(" · ")}</p>

      {comparisonError !== null && <ErrorBox message={comparisonError} />}
      {analyticsError !== null && <ErrorBox message={analyticsError} />}

      {loading ? (
        <Loading text="Comparando sesiones…" />
      ) : (
        <>
          {comparison === null ? (
            <EmptyState>No hay datos de comparación.</EmptyState>
          ) : (
            <>
              <ComparisonBars comparison={comparison} />
              <div className="section-heading comparison-table-heading">
                <div>
                  <p className="eyebrow">VALORES Y PROCEDENCIA</p>
                  <h2>Detalle por sesión</h2>
                </div>
              </div>
              <div className="table-wrap">
                <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Variable</TableHead>
                    <TableHead>Unidad</TableHead>
                    {comparison.sessions.map((session) => (
                      <TableHead key={session.session_id} className="num">
                        {session.session_id}
                      </TableHead>
                    ))}
                    <TableHead className="num">Δ (última − primera)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {comparison.variables.map((variable) => (
                    <TableRow key={variable.name}>
                      <TableCell>
                        <strong>
                          {VARIABLE_LABELS[variable.name] ?? variable.name}
                        </strong>
                      </TableCell>
                      <TableCell>{variable.unit || "—"}</TableCell>
                      {comparison.sessions.map((session) => {
                        const point = variable.points.find(
                          (p) => p.session_id === session.session_id,
                        );
                        if (!point || !point.available) {
                          return (
                            <TableCell key={session.session_id} className="num">
                              <span className="na">No disponible</span>
                            </TableCell>
                        );
                        }
                        return (
                          <TableCell key={session.session_id} className="num">
                            {point.value === null ? (
                              <span className="na">No disponible</span>
                            ) : (
                              `${Number(point.value.toFixed(3))} ${variable.unit}`.trim()
                            )}
                          </TableCell>
                        );
                      })}
                      <TableCell className="num">
                        <Delta value={variable.delta} unit={variable.unit} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                </Table>
              </div>
            </>
          )}

          {canViewRecommendations ? (
            <Card className="card recommendations-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">
                    {isTeacher ? "REVISIÓN DOCENTE" : "RETROALIMENTACIÓN APROBADA"}
                  </p>
                  <h2>Analítica y recomendaciones</h2>
                </div>
                <Badge className="badge review-badge">Uso informativo</Badge>
              </div>

              {analytics === null ? (
                <EmptyState>No hay un resultado analítico disponible.</EmptyState>
              ) : (
                <>
                  <p className="muted small">
                    Sesiones analizadas: {analytics.descriptive.sessions_analyzed} ·
                    dataset {analytics.dataset_version} · estado {analytics.execution_status}
                  </p>

                  <div
                    className={analytics.model_version === null ? "notice-box" : "success-box"}
                    style={{ marginBottom: 14 }}
                  >
                    {analytics.model_version === null
                      ? "Modelo predictivo: sin evaluación empírica."
                      : `Modelo predictivo: versión ${analytics.model_version}.`}
                  </div>

                  {analytics.recommendations.length === 0 ? (
                    <EmptyState>
                      {profile?.user_type === "student"
                        ? "Todavía no hay recomendaciones aprobadas para estas sesiones."
                        : "Todavía no se han generado recomendaciones para estas sesiones."}
                    </EmptyState>
                  ) : (
                    analytics.recommendations.map((recommendation) => (
                      <div className="rec" key={recommendation.recommendation_id}>
                        <div className="meta">
                          <Badge className="badge">{recommendation.rule_id}</Badge>{" "}
                          <Badge variant="secondary" className="badge grey">{recommendation.status}</Badge>{" "}
                          <Badge className="badge review-badge">
                            {recommendation.review_state === "PENDING_REVIEW"
                              ? "Pendiente de revisión docente"
                              : recommendation.review_state === "NOT_REQUIRED"
                                ? "Sin revisión: datos insuficientes"
                                : recommendation.review_state === "APPROVED"
                                  ? "Aprobada"
                                  : "Rechazada"}
                          </Badge>{" "}
                          sesiones: {recommendation.session_ids.join(", ")}
                          {recommendation.generated_at && (
                            <span> · generada {formatDate(recommendation.generated_at)}</span>
                          )}
                          {recommendation.reviewed_at && (
                            <span> · revisada {formatDate(recommendation.reviewed_at)}</span>
                          )}
                        </div>
                        <p style={{ marginTop: 6 }}>{recommendation.message}</p>
                        <strong className="small">Evidencia:</strong>
                        <ul className="evidence">
                          {recommendation.evidence.length === 0 ? (
                            <li className="muted">Sin evidencia registrada.</li>
                          ) : (
                            recommendation.evidence.map((item, index) => (
                              <li key={`${recommendation.recommendation_id}-${index}`}>
                                {item}
                              </li>
                            ))
                          )}
                        </ul>
                        <p className="small muted">Límites: {recommendation.limits}</p>
                        {isTeacher && recommendation.review?.review_note && (
                          <p className="small review-note">
                            Nota de revisión: {recommendation.review.review_note}
                          </p>
                        )}
                        {isTeacher &&
                          recommendation.status === "GENERATED" &&
                          recommendation.review_state === "PENDING_REVIEW" && (
                            <div className="review-controls">
                              <label className="field">
                                Nota para la decisión (opcional)
                                <textarea
                                  rows={2}
                                  maxLength={1000}
                                  value={reviewNotes[recommendation.recommendation_id] ?? ""}
                                  onChange={(event) =>
                                    setReviewNotes((current) => ({
                                      ...current,
                                      [recommendation.recommendation_id]: event.target.value,
                                    }))
                                  }
                                />
                              </label>
                              <div className="btn-row">
                                <Button
                                  className="btn approve-btn"
                                  disabled={reviewingId !== null}
                                  onClick={() => reviewRecommendation(recommendation.recommendation_id, "APPROVED")}
                                >
                                  {reviewingId === recommendation.recommendation_id
                                    ? "Guardando…"
                                    : "Aprobar para el estudiante"}
                                </Button>
                                <Button
                                  variant="outline"
                                  className="btn reject-btn"
                                  disabled={reviewingId !== null}
                                  onClick={() => reviewRecommendation(recommendation.recommendation_id, "REJECTED")}
                                >
                                  Rechazar
                                </Button>
                              </div>
                            </div>
                          )}
                      </div>
                    ))
                  )}

                  {isTeacher && analytics.execution_status !== "INSUFFICIENT_DATA" && (
                      <div className="btn-row">
                        <Button
                          className="btn"
                          onClick={generateRecommendations}
                          disabled={generating}
                        >
                          {generating
                            ? "Generando…"
                            : analytics.recommendations.length === 0
                              ? "Generar para revisión docente"
                              : "Buscar recomendaciones nuevas"}
                        </Button>
                      </div>
                    )}

                  <div className="notice-box">
                    <strong>Límites del análisis:</strong> {analytics.limits}
                    <br />
                    {analytics.evaluation.note}
                  </div>
                </>
              )}
            </Card>
          ) : (
            <div className="notice-box student-review-note" role="status">
              La consulta de analítica y recomendaciones está reservada a Docentes y Estudiantes.
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<Loading text="Cargando comparación…" />}>
      <CompareContent />
    </Suspense>
  );
}
