"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpRight, Search, Users } from "lucide-react";

import { api, ApiError } from "@/services/apiClient";
import { isStaff, useRequireAuth } from "@/services/auth";
import type { Athlete, SessionListItem } from "@/types/contracts";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorBox, Loading, formatDate } from "@/components/ui";

interface AthleteActivity {
  sessions: number;
  latest: SessionListItem | null;
}

export default function AthletesPage() {
  const { profile, ready } = useRequireAuth();
  const router = useRouter();
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [query, setQuery] = useState("");
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
    Promise.all([api.listAthletes(), api.listSessions()])
      .then(([athleteRows, sessionRows]) => {
        if (cancelled) return;
        setAthletes(athleteRows);
        setSessions(sessionRows);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof ApiError
              ? cause.detail
              : "No se pudo cargar el roster del CADI.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ready, profile, router]);

  const activityByAthlete = useMemo(() => {
    const result = new Map<string, AthleteActivity>();
    for (const session of sessions) {
      const activity = result.get(session.athlete_id) ?? { sessions: 0, latest: null };
      activity.sessions += 1;
      if (
        activity.latest === null ||
        new Date(session.timestamp).getTime() > new Date(activity.latest.timestamp).getTime()
      ) {
        activity.latest = session;
      }
      result.set(session.athlete_id, activity);
    }
    return result;
  }, [sessions]);

  const filteredAthletes = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("es");
    if (!normalized) return athletes;
    return athletes.filter((athlete) =>
      [athlete.athlete_id, athlete.label, athlete.group]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLocaleLowerCase("es").includes(normalized)),
    );
  }, [athletes, query]);

  if (!ready || profile === null || loading) return <Loading text="Cargando roster…" />;

  if (!isStaff(profile)) return <Loading text="Redirigiendo…" />;

  return (
    <div className="container roster-page">
      <div className="page-heading roster-heading">
        <div>
          <p className="eyebrow">CATÁLOGO TÉCNICO · DATOS SEUDONIMIZADOS</p>
          <h1 className="page-title">Atletas</h1>
          <p className="page-subtitle">
            Consulta el roster y el historial asociado a cada código CADI.
          </p>
        </div>
        <div className="roster-total">
          <Users size={17} aria-hidden="true" />
          <strong>{athletes.length}</strong>
          <span>registros</span>
        </div>
      </div>

      {error && <ErrorBox message={error} />}

      <section className="roster-toolbar" aria-label="Buscar atletas">
        <Label className="roster-search-label" htmlFor="athlete-search">
          <Search size={16} aria-hidden="true" />
          <span>Buscar por código, alias o grupo</span>
          <Input
            id="athlete-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="ATL-0001"
          />
        </Label>
        <span className="roster-result-count" aria-live="polite">
          {filteredAthletes.length} de {athletes.length}
        </span>
      </section>

      {filteredAthletes.length === 0 ? (
        <EmptyState>
          {athletes.length === 0
            ? "El catálogo aún no contiene atletas. Puedes registrar un código al importar sesiones."
            : "No hay atletas que coincidan con la búsqueda."}
        </EmptyState>
      ) : (
        <div className="roster-grid">
          {filteredAthletes.map((athlete) => {
            const activity = activityByAthlete.get(athlete.athlete_id) ?? {
              sessions: 0,
              latest: null,
            };
            return (
              <Link
                className="roster-athlete-card"
                href={`/athletes/${encodeURIComponent(athlete.athlete_id)}`}
                key={athlete.athlete_id}
              >
                <div className="roster-athlete-card-top">
                  <span className="roster-avatar" aria-hidden="true">
                    {athlete.athlete_id.slice(-2)}
                  </span>
                  <ArrowUpRight size={17} aria-hidden="true" />
                </div>
                <p className="eyebrow">CÓDIGO CADI</p>
                <h2>{athlete.athlete_id}</h2>
                <p className="roster-alias">
                  {athlete.label ?? "Sin alias académico registrado"}
                </p>
                <div className="roster-card-meta">
                  {athlete.group ? (
                    <Badge variant="secondary">{athlete.group}</Badge>
                  ) : (
                    <Badge variant="outline">Grupo no informado</Badge>
                  )}
                  <span>{activity.sessions} sesiones</span>
                </div>
                <div className="roster-card-footer">
                  <span>
                    Última prueba: {activity.latest ? formatDate(activity.latest.timestamp) : "Sin sesiones"}
                  </span>
                  <span>Registro {athlete.registered_at}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
