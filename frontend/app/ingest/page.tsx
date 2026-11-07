"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, api } from "@/services/apiClient";
import { isStaff, useRequireAuth } from "@/services/auth";
import type { IngestContract, IngestResult } from "@/types/contracts";
import { ErrorBox, Loading, errorMessage } from "@/components/ui";
import { Button } from "@/components/ui/button";

const SAMPLE_CONTRACT: IngestContract = {
  session_id: "SES-DEMO-001",
  athlete_id: "ATL-0001",
  timestamp: new Date().toISOString(),
  test_type: "prueba de 10 m con salida de tacos",
  metrics: {
    posture: null,
    speed: { avg: 6.2, max: 7.1, unit: "m/s", series: [{ t: 0, v: 4.8 }, { t: 0.5, v: 6.2 }] },
    stride: null,
    cadence: null,
  },
  metadata: {
    source_system: "Athletic_Export_FaseI",
    schema_version: "1.0.0",
    observation: "Ejemplo sintético; cambia el session_id antes de enviar.",
  },
};

export default function IngestPage() {
  const { profile, ready } = useRequireAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [payload, setPayload] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ingestErrors, setIngestErrors] = useState<IngestResult["errors"]>([]);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rejected, setRejected] = useState(false);

  // Los estudiantes no tienen acceso a la ingesta.
  useEffect(() => {
    if (ready && profile !== null && !isStaff(profile)) {
      router.replace("/dashboard");
    }
  }, [ready, profile, router]);

  if (!ready || profile === null) return <Loading />;
  if (!isStaff(profile)) return <Loading text="Sin acceso a la ingesta…" />;

  const handleFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      setPayload(String(reader.result ?? ""));
    };
    reader.onerror = () => setError("No se pudo leer el archivo.");
    reader.readAsText(file);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIngestErrors([]);
    setResult(null);
    setRejected(false);

    let parsed: unknown;
    try {
      parsed = JSON.parse(payload);
    } catch (err) {
      setError(
        `El JSON no es válido: ${err instanceof Error ? err.message : "error de sintaxis"}`,
      );
      return;
    }

    const isSingle =
      parsed !== null && typeof parsed === "object" && !Array.isArray(parsed);
    const isBatch = Array.isArray(parsed);
    if (!isSingle && !isBatch) {
      setError("El contenido debe ser un objeto contrato o un arreglo de ellos.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.ingestSessions(
        parsed as IngestContract | IngestContract[],
      );
      setResult(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
        if (err.errors !== undefined) {
          setIngestErrors(err.errors);
          setRejected(true);
        }
      } else {
        setError(errorMessage(err));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container ingest-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">DOCENTE / ADMINISTRADOR TÉCNICO</p>
          <h1 className="page-title">Ingesta de sesiones</h1>
          <p className="page-subtitle">
            Valida una exportación JSON antes de agregarla al histórico. La operación por lote es atómica.
          </p>
        </div>
        <span className="badge">Contrato versionado · Tabla 12</span>
      </div>

      {error !== null && <ErrorBox message={error} />}

      {rejected && (
        <div className="error-box" role="alert">
          La ingesta fue rechazada: <strong>nada se persistió</strong>.
        </div>
      )}

      {result !== null && (
        <div className="success-box" role="status">
          Aceptadas: <strong>{result.accepted}</strong>
          {result.rejected > 0 && (
            <>
              {" "}
              · rechazadas: <strong>{result.rejected}</strong>
            </>
          )}
          <br />
          Sesiones guardadas:{" "}
          {result.session_ids.length > 0
            ? result.session_ids.join(", ")
            : "ninguna"}
        </div>
      )}

      <div className="ingest-layout">
      <form className="card ingest-form" onSubmit={handleSubmit}>
        <div className="section-heading ingest-form-heading">
          <div>
            <p className="eyebrow">CARGA DE CONTRATO</p>
            <h2>Selecciona o pega un JSON</h2>
          </div>
          {fileName && <span className="file-name">{fileName}</span>}
        </div>
        <label className="field">
          Contenido del contrato
          <textarea
            required
            spellCheck={false}
            placeholder={`{
  "session_id": "SES-0001",
  "athlete_id": "ATL-0001",
  "timestamp": "2026-01-15T10:00:00Z",
  "test_type": "prueba de 10 m con salida de tacos",
  "metrics": { "speed": { "avg": 7.1, "max": 7.8, "unit": "m/s", "series": [] } },
  "metadata": { "source_system": "csv_fase1", "schema_version": "1.0" }
}`}
            value={payload}
            onChange={(event) => setPayload(event.target.value)}
          />
        </label>

        <div className="btn-row" style={{ marginTop: 0 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            onChange={handleFile}
            style={{ display: "none" }}
          />
          <Button
            type="button"
            variant="outline"
            className="btn secondary"
            onClick={() => fileInputRef.current?.click()}
          >
            Cargar archivo .json
          </Button>
          <Button
            type="button"
            variant="outline"
            className="btn secondary"
            onClick={() => {
              setFileName(null);
              setPayload(JSON.stringify(SAMPLE_CONTRACT, null, 2));
            }}
          >
            Usar ejemplo
          </Button>
          <Button type="submit" className="btn" disabled={submitting}>
            {submitting ? "Enviando…" : "Enviar ingesta"}
          </Button>
        </div>
      </form>

      <aside className="card ingest-guide">
        <p className="eyebrow">VALIDACIÓN</p>
        <h2>Antes de enviar</h2>
        <ul>
          <li>Incluye `session_id`, `athlete_id`, fecha ISO 8601 y tipo de prueba.</li>
          <li>Indica `metadata.source_system` y `metadata.schema_version`.</li>
          <li>Los valores nulos se conservan como «No disponible».</li>
          <li>Si un registro falla, no se persiste ningún elemento del lote.</li>
        </ul>
        <div className="notice-box">
          Evita incluir nombres, documentos u otros datos personales en el archivo.
        </div>
      </aside>
      </div>

      {ingestErrors.length > 0 && (
        <div className="card ingest-errors">
          <p className="eyebrow">LOTE NO PERSISTIDO</p>
          <h2>Errores de validación</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Sesión</th>
                  <th>Campo</th>
                  <th>Mensaje</th>
                </tr>
              </thead>
              <tbody>
                {ingestErrors.map((item, index) => (
                  <tr key={`${item.session_id}-${item.field}-${index}`}>
                    <td>{item.session_id}</td>
                    <td>
                      <code>{item.field}</code>
                    </td>
                    <td>{item.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
