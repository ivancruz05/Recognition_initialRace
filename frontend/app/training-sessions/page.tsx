"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/services/apiClient";
import { useRequireAuth } from "@/services/auth";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBox, Loading, errorMessage, formatDate } from "@/components/ui";
import type {
  Athlete,
  AttendanceStatus,
  SessionListItem,
  TrainingSession,
  TrainingSessionPayload,
} from "@/types/contracts";

type TrainingForm = {
  athlete_id: string;
  timestamp: string;
  duration_minutes: string;
  training_type: string;
  attendance_status: AttendanceStatus;
  coach: string;
  location: string;
  follow_up_notes: string;
  sprint_session_ids: string[];
};

const ATTENDANCE_LABELS: Record<AttendanceStatus, string> = {
  present: "Presente",
  absent: "Ausente",
  excused: "Justificada",
};

function localDateTimeValue(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function emptyForm(athleteId = ""): TrainingForm {
  return {
    athlete_id: athleteId,
    timestamp: localDateTimeValue(new Date().toISOString()),
    duration_minutes: "60",
    training_type: "",
    attendance_status: "present",
    coach: "",
    location: "",
    follow_up_notes: "",
    sprint_session_ids: [],
  };
}

function toForm(session: TrainingSession): TrainingForm {
  return {
    athlete_id: session.athlete_id,
    timestamp: localDateTimeValue(session.timestamp),
    duration_minutes: String(session.duration_minutes),
    training_type: session.training_type,
    attendance_status: session.attendance_status,
    coach: session.coach,
    location: session.location,
    follow_up_notes: session.follow_up_notes,
    sprint_session_ids: session.sprint_session_ids,
  };
}

function toPayload(form: TrainingForm): TrainingSessionPayload {
  return {
    athlete_id: form.athlete_id,
    timestamp: new Date(form.timestamp).toISOString(),
    duration_minutes: Number(form.duration_minutes),
    training_type: form.training_type.trim(),
    attendance_status: form.attendance_status,
    coach: form.coach.trim(),
    location: form.location.trim(),
    follow_up_notes: form.follow_up_notes.trim(),
    sprint_session_ids: form.sprint_session_ids,
  };
}

export default function TrainingSessionsPage() {
  const { profile, ready } = useRequireAuth();
  const isStaff =
    profile?.user_type === "teacher" || profile?.user_type === "admin";

  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [athleteFilter, setAthleteFilter] = useState("");
  const [form, setForm] = useState<TrainingForm>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [sprintTests, setSprintTests] = useState<SessionListItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [testsLoading, setTestsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testsError, setTestsError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    if (!profile) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTrainingSessions(
        isStaff ? athleteFilter || undefined : undefined,
      );
      setSessions(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [profile, isStaff, athleteFilter]);

  useEffect(() => {
    if (ready && profile) void loadSessions();
  }, [ready, profile?.id, loadSessions]);

  useEffect(() => {
    if (!ready || !profile || !isStaff) return;
    let cancelled = false;
    api
      .listAthletes()
      .then((data) => {
        if (!cancelled) {
          setAthletes(data);
          setForm((current) => ({
            ...current,
            athlete_id: current.athlete_id || data[0]?.athlete_id || "",
          }));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [ready, profile?.id, isStaff]);

  useEffect(() => {
    if (!showForm || !isStaff || !form.athlete_id) {
      setSprintTests([]);
      return;
    }
    let cancelled = false;
    setTestsLoading(true);
    setTestsError(null);
    api
      .listSessions({ athlete_id: form.athlete_id })
      .then((data) => {
        if (!cancelled) {
          setSprintTests(
            data.filter(
              (test) =>
                test.training_session_id === null ||
                test.training_session_id === editingId,
            ),
          );
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setTestsError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setTestsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [showForm, isStaff, form.athlete_id, editingId]);

  if (!ready || !profile) return <Loading />;

  const openCreateForm = () => {
    setEditingId(null);
    setForm(emptyForm(athleteFilter || athletes[0]?.athlete_id || ""));
    setShowForm(true);
    setError(null);
    setSuccess(null);
  };

  const openEditForm = (session: TrainingSession) => {
    setEditingId(session.id);
    setForm(toForm(session));
    setShowForm(true);
    setError(null);
    setSuccess(null);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setTestsError(null);
  };

  const toggleSprintTest = (sessionId: string) => {
    setForm((current) => ({
      ...current,
      sprint_session_ids: current.sprint_session_ids.includes(sessionId)
        ? current.sprint_session_ids.filter((id) => id !== sessionId)
        : [...current.sprint_session_ids, sessionId],
    }));
  };

  const submitForm = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const payload = toPayload(form);
      if (editingId === null) {
        await api.createTrainingSession(payload);
        setSuccess("Entrenamiento registrado.");
      } else {
        await api.updateTrainingSession(editingId, payload);
        setSuccess("Entrenamiento actualizado.");
      }
      closeForm();
      await loadSessions();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container training-sessions-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">HISTORIAL INDIVIDUAL</p>
          <h1 className="page-title">Entrenamientos</h1>
          <p className="page-subtitle">
            Asistencia, contexto, seguimiento y pruebas asociadas por atleta.
          </p>
        </div>
        {isStaff && (
          <Button type="button" className="btn" onClick={openCreateForm}>
            Nuevo entrenamiento
          </Button>
        )}
      </div>

      {error !== null && <ErrorBox message={error} />}
      {success !== null && (
        <div className="success-box" role="status">
          {success}
        </div>
      )}

      {isStaff && (
        <section className="card training-filter-card">
          <label className="field" htmlFor="training-athlete-filter">
            Atleta
            <select
              id="training-athlete-filter"
              value={athleteFilter}
              onChange={(event) => setAthleteFilter(event.target.value)}
            >
              <option value="">Todos los atletas</option>
              {athletes.map((athlete) => (
                <option key={athlete.athlete_id} value={athlete.athlete_id}>
                  {athlete.athlete_id}
                  {athlete.label ? ` · ${athlete.label}` : ""}
                  {athlete.group ? ` · ${athlete.group}` : ""}
                </option>
              ))}
            </select>
          </label>
        </section>
      )}

      {showForm && isStaff && (
        <form className="card training-form" onSubmit={submitForm}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                {editingId === null ? "NUEVO REGISTRO" : "EDITAR REGISTRO"}
              </p>
              <h2>{editingId === null ? "Datos del entrenamiento" : "Actualizar entrenamiento"}</h2>
            </div>
          </div>

          <div className="training-form-grid">
            <label className="field" htmlFor="training-athlete">
              Atleta
              <select
                id="training-athlete"
                required
                value={form.athlete_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    athlete_id: event.target.value,
                    sprint_session_ids: [],
                  })
                }
              >
                <option value="" disabled>
                  Selecciona un atleta
                </option>
                {athletes.map((athlete) => (
                  <option key={athlete.athlete_id} value={athlete.athlete_id}>
                    {athlete.athlete_id}
                    {athlete.label ? ` · ${athlete.label}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="field" htmlFor="training-timestamp">
              Fecha y hora
              <input
                id="training-timestamp"
                type="datetime-local"
                required
                value={form.timestamp}
                onChange={(event) =>
                  setForm({ ...form, timestamp: event.target.value })
                }
              />
            </label>
            <label className="field" htmlFor="training-duration">
              Duración (minutos)
              <input
                id="training-duration"
                type="number"
                min="1"
                max="1440"
                required
                value={form.duration_minutes}
                onChange={(event) =>
                  setForm({ ...form, duration_minutes: event.target.value })
                }
              />
            </label>
            <label className="field" htmlFor="training-type">
              Tipo de entrenamiento
              <input
                id="training-type"
                type="text"
                maxLength={120}
                required
                value={form.training_type}
                onChange={(event) =>
                  setForm({ ...form, training_type: event.target.value })
                }
              />
            </label>
            <label className="field" htmlFor="training-attendance">
              Asistencia
              <select
                id="training-attendance"
                value={form.attendance_status}
                onChange={(event) =>
                  setForm({
                    ...form,
                    attendance_status: event.target.value as AttendanceStatus,
                  })
                }
              >
                {Object.entries(ATTENDANCE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field" htmlFor="training-coach">
              Entrenador
              <input
                id="training-coach"
                type="text"
                maxLength={150}
                value={form.coach}
                onChange={(event) =>
                  setForm({ ...form, coach: event.target.value })
                }
              />
            </label>
            <label className="field" htmlFor="training-location">
              Lugar
              <input
                id="training-location"
                type="text"
                maxLength={150}
                value={form.location}
                onChange={(event) =>
                  setForm({ ...form, location: event.target.value })
                }
              />
            </label>
          </div>

          <label className="field" htmlFor="training-follow-up">
            Notas de seguimiento
            <textarea
              id="training-follow-up"
              maxLength={4000}
              value={form.follow_up_notes}
              onChange={(event) =>
                setForm({ ...form, follow_up_notes: event.target.value })
              }
            />
          </label>

          <fieldset className="training-tests">
            <legend>Pruebas de sprint asociadas</legend>
            {testsLoading ? (
              <p className="small muted">Cargando pruebas del atleta…</p>
            ) : testsError !== null ? (
              <ErrorBox message={testsError} />
            ) : sprintTests.length === 0 ? (
              <p className="small muted">
                Este atleta todavía no tiene pruebas de sprint registradas.
              </p>
            ) : (
              <div className="training-test-options">
                {sprintTests.map((test) => (
                  <label className="training-test-option" key={test.session_id}>
                    <input
                      type="checkbox"
                      checked={form.sprint_session_ids.includes(test.session_id)}
                      onChange={() => toggleSprintTest(test.session_id)}
                    />
                    <span>
                      <strong>{test.session_id}</strong>
                      <span className="small muted">
                        {formatDate(test.timestamp)} · {test.test_type}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            )}
          </fieldset>

          <div className="btn-row">
            <Button
              type="submit"
              className="btn"
              disabled={submitting || testsLoading || !form.athlete_id}
            >
              {submitting
                ? "Guardando…"
                : editingId === null
                  ? "Guardar entrenamiento"
                  : "Guardar cambios"}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="btn secondary"
              onClick={closeForm}
              disabled={submitting}
            >
              Cancelar
            </Button>
          </div>
        </form>
      )}

      {loading ? (
        <Loading text="Cargando entrenamientos…" />
      ) : sessions.length === 0 ? (
        <EmptyState>No hay entrenamientos para mostrar.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Atleta</th>
                <th>Entrenamiento</th>
                <th>Asistencia</th>
                <th>Contexto y seguimiento</th>
                <th>Pruebas</th>
                {isStaff && <th>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr
                  key={session.id}
                  id={`training-session-${session.id}`}
                >
                  <td>
                    {formatDate(session.timestamp)}
                    <br />
                    <span className="small muted">
                      {session.duration_minutes} min
                    </span>
                  </td>
                  <td>{session.athlete_id}</td>
                  <td>{session.training_type}</td>
                  <td>
                    <span className={`badge attendance-${session.attendance_status}`}>
                      {ATTENDANCE_LABELS[session.attendance_status]}
                    </span>
                  </td>
                  <td>
                    {session.coach && <div>Entrenador: {session.coach}</div>}
                    {session.location && <div>Lugar: {session.location}</div>}
                    {session.follow_up_notes && (
                      <div className="small muted">{session.follow_up_notes}</div>
                    )}
                    {!session.coach &&
                      !session.location &&
                      !session.follow_up_notes && (
                        <span className="muted">Sin notas</span>
                      )}
                  </td>
                  <td>
                    {session.sprint_session_ids.length > 0 ? (
                      <div className="training-sprint-links">
                        {session.sprint_session_ids.map((sessionId) => (
                          <Link
                            key={sessionId}
                            href={`/sessions/${encodeURIComponent(sessionId)}`}
                          >
                            {sessionId}
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <span className="muted">Sin pruebas vinculadas</span>
                    )}
                  </td>
                  {isStaff && (
                    <td>
                      <Button
                        type="button"
                        variant="outline"
                        className="btn secondary"
                        onClick={() => openEditForm(session)}
                      >
                        Editar
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
