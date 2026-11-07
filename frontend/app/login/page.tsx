"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/services/apiClient";
import { useAuth } from "@/services/auth";
import { ErrorBox } from "@/components/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Mode = "login" | "register";

export default function LoginPage() {
  const { profile, ready, login, register } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (ready && profile !== null) {
      router.replace("/dashboard");
    }
  }, [ready, profile, router]);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password);
      }
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("No se pudo completar la operación.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-wrap">
      <section className="login-story" aria-labelledby="login-story-title">
        <p className="eyebrow">CENTRO ACADÉMICO DEPORTIVO · FASE II</p>
        <h2 id="login-story-title">
          Cada prueba cuenta una historia de movimiento.
        </h2>
        <p className="login-story-copy">
          Consulta sesiones, compara variables y conserva el contexto de cada
          medición. Los datos ausentes permanecen visibles como tales.
        </p>
        <div className="login-facts" aria-label="Alcance del sistema">
          <div><strong>04</strong><span>variables deportivas</span></div>
          <div><strong>10 m</strong><span>prueba de velocidad</span></div>
          <div><strong>RF-10</strong><span>trazabilidad de origen</span></div>
        </div>
        <div className="login-track" aria-hidden="true">
          <span /><span /><span /><span />
        </div>
        <p className="login-story-foot">Universidad de Cundinamarca · CADI</p>
      </section>
      <div className="login-card">
        <p className="eyebrow">ACCESO SEGURO</p>
        <h1>{mode === "login" ? "Bienvenido de nuevo" : "Crear cuenta"}</h1>
        <p className="sub">
          {mode === "login"
            ? "Inicia sesión para consultar el histórico del CADI."
            : "Regístrate como estudiante para consultar tus sesiones."}
        </p>

        {error !== null && <ErrorBox message={error} />}

        <form onSubmit={handleSubmit}>
          <Label className="field" htmlFor="login-email">
            Correo electrónico
            <Input
              id="login-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Label>
          <Label className="field" htmlFor="login-password">
            Contraseña
            <Input
              id="login-password"
              type="password"
              required
              minLength={8}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Label>
          <Button className="btn" type="submit" disabled={submitting}>
            {submitting
              ? "Enviando…"
              : mode === "login"
                ? "Iniciar sesión"
                : "Registrarme"}
          </Button>
        </form>

        <div className="btn-row">
          <Button
            type="button"
            variant="outline"
            className="btn secondary"
            onClick={() => switchMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login"
              ? "¿No tienes cuenta? Regístrate"
              : "¿Ya tienes cuenta? Inicia sesión"}
          </Button>
        </div>
        <p className="small muted" style={{ marginBottom: 0 }}>
          El registro crea siempre una cuenta de estudiante.
        </p>
      </div>
    </div>
  );
}
