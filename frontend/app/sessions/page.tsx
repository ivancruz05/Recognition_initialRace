"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/services/apiClient";
import { useRequireAuth } from "@/services/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Athlete, SessionFilters, SessionListItem } from "@/types/contracts";
import {
  EmptyState,
  ErrorBox,
  Loading,
  VARIABLE_LABELS,
  errorMessage,
  formatDate,
} from "@/components/ui";

const EMPTY_FILTERS: SessionFilters = {
  athlete_id: "",
  session_id: "",
  test_type: "",
  date_from: "",
  date_to: "",
};

const MAX_COMPARE = 4;

export default function SessionsPage() {
  const { profile, ready } = useRequireAuth();
  const router = useRouter();

  const [filters, setFilters] = useState<SessionFilters>(EMPTY_FILTERS);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [athletesError, setAthletesError] = useState<string | null>(null);
  const requestNumber = useRef(0);
  const canSelectAthlete = profile?.user_type === "teacher" || profile?.user_type === "admin";

  const load = useCallback(
    (activeFilters: SessionFilters) => {
      const currentRequest = ++requestNumber.current;
      setLoading(true);
      setError(null);
      api
        .listSessions(activeFilters)
        .then((data) => {
          if (currentRequest === requestNumber.current) setSessions(data);
        })
        .catch((err: unknown) => {
          if (currentRequest === requestNumber.current) setError(errorMessage(err));
        })
        .finally(() => {
          if (currentRequest === requestNumber.current) setLoading(false);
        });
    },
    [],
  );

  useEffect(() => {
    if (!ready || profile === null) return;
    // Actualización reactiva con debounce: no hace falta recargar la página.
    const timer = window.setTimeout(() => load(filters), 220);
    return () => window.clearTimeout(timer);
  }, [ready, profile?.id, filters, load]);

  useEffect(() => {
    if (!ready || !canSelectAthlete) return;
    let cancelled = false;
    api.listAthletes()
      .then((data) => {
        if (!cancelled) setAthletes(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setAthletesError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [ready, profile?.id, canSelectAthlete]);

  if (!ready || profile === null) return <Loading />;

  const applyFilters = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    load(filters);
  };

  const clearFilters = () => {
    setFilters({ ...EMPTY_FILTERS });
    setSelected([]);
  };

  const toggleSelected = (sessionId: string) => {
    setSelected((current) => {
      if (current.includes(sessionId)) {
        return current.filter((id) => id !== sessionId);
      }
      if (current.length >= MAX_COMPARE) return current;
      return [...current, sessionId];
    });
  };

  const compare = () => {
    router.push(`/sessions/compare?ids=${encodeURIComponent(selected.join(","))}`);
  };

  const atLimit = selected.length >= MAX_COMPARE;

  return (
    <div className="container sessions-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">HISTÓRICO CADI</p>
          <h1 className="page-title">Sesiones</h1>
      <p className="page-subtitle">
            Filtra el histórico y compara de dos a {MAX_COMPARE} sesiones.
      </p>
        </div>
        <div className="result-count" aria-live="polite">
          {loading ? "Actualizando…" : `${sessions.length} sesiones`}
        </div>
      </div>

      <form className="card filter-card" onSubmit={applyFilters} aria-label="Filtros de sesiones">
        {canSelectAthlete && (
          <Label className="field" htmlFor="filter-athlete">
            Atleta
            <Select
              value={filters.athlete_id || "all"}
              onValueChange={(value) =>
                setFilters({
                  ...filters,
                  athlete_id: value === null || value === "all" ? "" : value,
                })
              }
            >
              <SelectTrigger className="form-select" id="filter-athlete">
                <SelectValue placeholder="Todos los atletas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los atletas</SelectItem>
                {athletes.map((athlete) => (
                  <SelectItem key={athlete.athlete_id} value={athlete.athlete_id}>
                    {athlete.athlete_id}{athlete.label ? ` · ${athlete.label}` : ""}{athlete.group ? ` · ${athlete.group}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Label>
        )}
        <Label className="field" htmlFor="filter-session">
          Sesión
          <Input
            id="filter-session"
            type="text"
            placeholder="SES-F1-001"
            value={filters.session_id ?? ""}
            onChange={(event) =>
              setFilters({ ...filters, session_id: event.target.value })
            }
          />
        </Label>
        <Label className="field" htmlFor="filter-test-type">
          Prueba
          <Input
            id="filter-test-type"
            type="text"
            placeholder="prueba de 10 m…"
            value={filters.test_type ?? ""}
            onChange={(event) =>
              setFilters({ ...filters, test_type: event.target.value })
            }
          />
        </Label>
        <Label className="field" htmlFor="filter-date-from">
          Desde
          <Input
            id="filter-date-from"
            type="date"
            value={filters.date_from ?? ""}
            onChange={(event) =>
              setFilters({ ...filters, date_from: event.target.value })
            }
          />
        </Label>
        <Label className="field" htmlFor="filter-date-to">
          Hasta
          <Input
            id="filter-date-to"
            type="date"
            value={filters.date_to ?? ""}
            onChange={(event) =>
              setFilters({ ...filters, date_to: event.target.value })
            }
          />
        </Label>
        <div className="btn-row" style={{ marginTop: 0 }}>
          <Button className="btn" type="submit" disabled={loading}>
            Actualizar resultados
          </Button>
          <Button
            variant="outline"
            className="btn secondary"
            type="button"
            onClick={clearFilters}
          >
            Limpiar
          </Button>
        </div>
      </form>

      {athletesError !== null && <ErrorBox message={`No se pudo cargar el selector de atletas: ${athletesError}`} />}
      {error !== null && <ErrorBox message={error} />}

      <div className="btn-row" style={{ marginTop: 0, marginBottom: 12 }}>
        <Button
          type="button"
          className="btn"
          onClick={compare}
          disabled={selected.length < 2}
        >
          Comparar ({selected.length}/{MAX_COMPARE})
        </Button>
        <span className="small muted">
          {atLimit
            ? "Límite de comparación alcanzado."
            : "Marca al menos dos sesiones para comparar."}
        </span>
      </div>

      {loading ? (
        <Loading text="Cargando sesiones…" />
      ) : sessions.length === 0 ? (
        <EmptyState>No hay sesiones que coincidan con los filtros.</EmptyState>
      ) : (
        <div className="table-wrap">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Comparar</TableHead>
                <TableHead>Sesión</TableHead>
                <TableHead>Atleta</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Prueba</TableHead>
                <TableHead>Origen</TableHead>
                <TableHead>Variables</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.map((session) => {
                const isSelected = selected.includes(session.session_id);
                return (
                  <TableRow key={session.session_id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        aria-label={`Seleccionar ${session.session_id}`}
                        checked={isSelected}
                        disabled={!isSelected && atLimit}
                        onChange={() => toggleSelected(session.session_id)}
                      />
                    </TableCell>
                    <TableCell>
                      <Link
                        className="table-primary-link"
                        href={`/sessions/${encodeURIComponent(session.session_id)}`}
                      >
                        {session.session_id}
                      </Link>
                    </TableCell>
                    <TableCell>{session.athlete_id}</TableCell>
                    <TableCell>{formatDate(session.timestamp)}</TableCell>
                    <TableCell>{session.test_type}</TableCell>
                    <TableCell className="small muted">
                      {session.source_system}
                      <br />
                      v{session.schema_version}
                    </TableCell>
                    <TableCell className="small">
                      {session.available_variables.length > 0
                        ? session.available_variables
                            .map((v) => VARIABLE_LABELS[v] ?? v)
                            .join(", ")
                        : "ninguna"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
