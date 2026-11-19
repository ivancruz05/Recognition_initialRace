"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, formatDate, VARIABLE_LABELS } from "@/components/ui";
import type { SessionListItem } from "@/types/contracts";
import { ArrowUpRight, Scale } from "lucide-react";

interface RecentSessionsTableProps {
  sessions: SessionListItem[];
  selectedSessions: string[];
  maxCompare: number;
  onToggleSelect: (sessionId: string) => void;
}

export function RecentSessionsTable({
  sessions,
  selectedSessions,
  maxCompare,
  onToggleSelect,
}: RecentSessionsTableProps) {
  return (
    <section className="section-card-wrapper" aria-labelledby="recent-sessions-title">
      <div className="section-card-header">
        <div>
          <h2 id="recent-sessions-title" className="text-base font-bold text-navy">
            Pruebas Registradas Recientes
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Selecciona entre 2 y {maxCompare} sesiones para comparar variables y sus unidades declaradas.
          </p>
        </div>
        <Link href="/sessions" className="text-link text-xs sm:text-sm">
          Ver todas las sesiones <span aria-hidden="true">→</span>
        </Link>
      </div>

      {sessions.length === 0 ? (
        <div style={{ padding: 28 }}>
          <EmptyState>
            No se encontraron sesiones que coincidan con los filtros seleccionados.
          </EmptyState>
        </div>
      ) : (
        <div className="table-wrap">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12 text-center">
                  <span className="sr-only">Selección</span>
                  <Scale className="w-4 h-4 mx-auto text-muted-foreground" aria-hidden="true" />
                </TableHead>
                <TableHead>Sesión / Origen</TableHead>
                <TableHead>Atleta</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Prueba</TableHead>
                <TableHead>Variables disponibles</TableHead>
                <TableHead className="text-right">Acción</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.map((session) => {
                const isSelected = selectedSessions.includes(session.session_id);
                const isMaxReached =
                  selectedSessions.length >= maxCompare && !isSelected;

                return (
                  <TableRow
                    key={session.session_id}
                    className={isSelected ? "bg-muted/40" : undefined}
                  >
                    <TableCell className="text-center align-middle">
                      <input
                        type="checkbox"
                        aria-label={`Seleccionar sesión ${session.session_id} para comparar`}
                        checked={isSelected}
                        disabled={isMaxReached}
                        onChange={() => onToggleSelect(session.session_id)}
                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed"
                        title={
                          isMaxReached
                            ? `Máximo ${maxCompare} sesiones permitidas para comparar.`
                            : undefined
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <strong className="text-navy font-mono text-sm">
                        {session.session_id}
                      </strong>
                      <span className="table-subline">
                        {session.source_system} · v{session.schema_version ?? "No disponible"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                        {session.athlete_id}
                      </span>
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs">
                      {formatDate(session.timestamp)}
                    </TableCell>
                    <TableCell className="text-xs">{session.test_type}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {session.available_variables.length > 0 ? (
                          session.available_variables.map((varName) => (
                            <Badge
                              key={varName}
                              variant="secondary"
                              className="text-[11px] py-0 px-1.5"
                            >
                              {VARIABLE_LABELS[varName] ?? varName}
                            </Badge>
                          ))
                        ) : (
                          <span className="na text-xs">No disponible</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right whitespace-nowrap">
                      <Link
                        className="row-link text-xs inline-flex items-center gap-1"
                        href={`/sessions/${encodeURIComponent(session.session_id)}`}
                        aria-label={`Abrir detalle de sesión ${session.session_id}`}
                      >
                        Abrir <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                      </Link>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}
