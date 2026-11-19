"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Profile } from "@/types/contracts";
import { ShieldCheck, ArrowUpRight } from "lucide-react";

interface DashboardHeroProps {
  profile: Profile;
  scopeLabel: string;
  isRefreshing: boolean;
  totalSessions: number;
}

export function DashboardHero({
  profile,
  scopeLabel,
  isRefreshing,
  totalSessions,
}: DashboardHeroProps) {
  const isTeacherOrAdmin =
    profile.user_type === "teacher" || profile.user_type === "admin";

  const roleLabel = {
    teacher: "Docente evaluador",
    student: "Atleta evaluado",
    admin: "Administrador técnico",
  }[profile.user_type];

  return (
    <header className="dashboard-hero" aria-labelledby="dashboard-title">
      <div className="dashboard-hero-title-group">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
          <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
            CADI Fase II · Laboratorio de Biomecánica
          </span>
        </div>

        <h1 id="dashboard-title" className="page-title text-navy font-bold tracking-tight">
          Monitoreo y Cinemática de Carrera
        </h1>

        <p className="page-subtitle text-sm text-muted-foreground max-w-xl">
          Consulta del histórico de pruebas, variables recibidas y procedencia de cada registro.
        </p>

        <div className="dashboard-badges-row mt-3">
          <span className="dashboard-scope-tag font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
            {scopeLabel}
          </span>
          <Badge variant="outline" className="text-xs">
            {roleLabel}
          </Badge>
          <span className="text-xs text-muted-foreground font-medium">
            {totalSessions} {totalSessions === 1 ? "prueba cargada" : "pruebas cargadas"}
          </span>
          {isRefreshing && (
            <Badge variant="secondary" className="text-xs animate-pulse text-amber-700 bg-amber-50 border-amber-200">
              Sincronizando…
            </Badge>
          )}
        </div>
      </div>

      <div className="dashboard-actions-group">
        {isTeacherOrAdmin && (
          <Link href="/ingest" className="btn secondary text-xs sm:text-sm">
            Nueva Ingesta <span aria-hidden="true">↗</span>
          </Link>
        )}
        <Link href="/sessions" className="btn text-xs sm:text-sm">
          Explorar Sesiones <ArrowUpRight className="w-3.5 h-3.5 ml-1 inline" />
        </Link>
      </div>
    </header>
  );
}
