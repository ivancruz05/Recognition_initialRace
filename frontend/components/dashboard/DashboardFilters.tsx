"use client";

import { Badge } from "@/components/ui/badge";
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
import type { Athlete, Profile, SessionFilters } from "@/types/contracts";
import { Filter, RotateCcw } from "lucide-react";

interface DashboardFiltersProps {
  filters: SessionFilters;
  athletes: Athlete[];
  profile: Profile;
  activeFiltersCount: number;
  onFilterChange: (key: keyof SessionFilters, value: string) => void;
  onClearFilters: () => void;
}

export function DashboardFilters({
  filters,
  athletes,
  profile,
  activeFiltersCount,
  onFilterChange,
  onClearFilters,
}: DashboardFiltersProps) {
  const isTeacherOrAdmin =
    profile.user_type === "teacher" || profile.user_type === "admin";

  return (
    <section className="dashboard-filters-card" aria-labelledby="filters-title">
      <div className="filters-header">
        <div className="filters-header-title">
          <Filter className="w-4 h-4 text-primary" aria-hidden="true" />
          <span id="filters-title">Filtros de consulta del panel</span>
          {activeFiltersCount > 0 && (
            <Badge variant="secondary" className="text-xs">
              {activeFiltersCount} activo{activeFiltersCount > 1 ? "s" : ""}
            </Badge>
          )}
        </div>
        {activeFiltersCount > 0 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClearFilters}
            className="text-xs text-muted-foreground hover:text-foreground h-8"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
            Limpiar filtros
          </Button>
        )}
      </div>

      <div className="filters-grid">
        {/* Selector de atleta según rol */}
        {isTeacherOrAdmin ? (
          <Label className="field" htmlFor="filter-athlete">
            Atleta
            <Select
              value={filters.athlete_id || "all"}
              onValueChange={(val) =>
                onFilterChange("athlete_id", val === "all" ? "" : (val ?? ""))
              }
            >
              <SelectTrigger id="filter-athlete" className="w-full">
                <SelectValue placeholder="Todos los atletas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los atletas</SelectItem>
                {athletes.map((athlete) => (
                  <SelectItem key={athlete.athlete_id} value={athlete.athlete_id}>
                    {athlete.athlete_id}
                    {athlete.label ? ` · ${athlete.label}` : ""}
                    {athlete.group ? ` (${athlete.group})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Label>
        ) : (
          <Label className="field" htmlFor="filter-student-athlete">
            Atleta asignado (RBAC)
            <Input
              id="filter-student-athlete"
              type="text"
              value={profile.athlete_id || "Sin código asignado"}
              disabled
              className="bg-muted text-muted-foreground cursor-not-allowed"
              title="Los estudiantes solo tienen autorización para consultar su propio historial de pruebas."
            />
          </Label>
        )}

        <Label className="field" htmlFor="filter-session-id">
          Sesión
          <Input
            id="filter-session-id"
            type="text"
            placeholder="SES-F1-…"
            value={filters.session_id ?? ""}
            onChange={(event) => onFilterChange("session_id", event.target.value)}
          />
        </Label>

        {/* Tipo de prueba */}
        <Label className="field" htmlFor="filter-test-type">
          Tipo de prueba
          <Input
            id="filter-test-type"
            type="text"
            placeholder="Ej. Velocidad 10 m…"
            value={filters.test_type ?? ""}
            onChange={(e) => onFilterChange("test_type", e.target.value)}
          />
        </Label>

        {/* Fecha desde */}
        <Label className="field" htmlFor="filter-date-from">
          Desde
          <Input
            id="filter-date-from"
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => onFilterChange("date_from", e.target.value)}
          />
        </Label>

        {/* Fecha hasta */}
        <Label className="field" htmlFor="filter-date-to">
          Hasta
          <Input
            id="filter-date-to"
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => onFilterChange("date_to", e.target.value)}
          />
        </Label>
      </div>
    </section>
  );
}
