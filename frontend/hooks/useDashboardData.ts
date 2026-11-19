"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/services/apiClient";
import type {
  Athlete,
  DashboardSummary,
  Profile,
  SessionFilters,
  SessionListItem,
} from "@/types/contracts";
import { errorMessage } from "@/components/ui";

export const EMPTY_FILTERS: SessionFilters = {
  athlete_id: "",
  session_id: "",
  test_type: "",
  date_from: "",
  date_to: "",
};

export interface UseDashboardDataReturn {
  filters: SessionFilters;
  summary: DashboardSummary | null;
  recentSessions: SessionListItem[];
  athletes: Athlete[];
  initialLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  athletesError: string | null;
  activeFiltersCount: number;
  handleFilterChange: (key: keyof SessionFilters, value: string) => void;
  handleClearFilters: () => void;
  reload: () => void;
}

/**
 * Hook de dominio para desacoplar el estado y ciclo de datos del Dashboard (Arquitectura Limpia).
 */
export function useDashboardData(
  profile: Profile | null,
  ready: boolean,
): UseDashboardDataReturn {
  const [filters, setFilters] = useState<SessionFilters>(EMPTY_FILTERS);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentSessions, setRecentSessions] = useState<SessionListItem[]>([]);
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [athletesError, setAthletesError] = useState<string | null>(null);

  const requestNumber = useRef(0);
  const isTeacherOrAdmin =
    profile?.user_type === "teacher" || profile?.user_type === "admin";

  // Catálogo de atletas (docente / admin)
  useEffect(() => {
    if (!ready || !isTeacherOrAdmin) return;
    let cancelled = false;
    api
      .listAthletes()
      .then((data) => {
        if (!cancelled) setAthletes(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setAthletesError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [ready, profile?.id, isTeacherOrAdmin]);

  // Carga reactiva con debounce de 220ms
  const loadData = useCallback(
    (activeFilters: SessionFilters) => {
      const currentRequest = ++requestNumber.current;
      setIsRefreshing(true);
      setError(null);

      Promise.all([
        api.dashboardSummary(activeFilters),
        api.listSessions(activeFilters),
      ])
        .then(([summaryData, sessionsData]) => {
          if (currentRequest === requestNumber.current) {
            setSummary(summaryData);
            setRecentSessions(sessionsData.slice(0, 8));
          }
        })
        .catch((err: unknown) => {
          if (currentRequest === requestNumber.current) {
            setError(errorMessage(err));
          }
        })
        .finally(() => {
          if (currentRequest === requestNumber.current) {
            setIsRefreshing(false);
            setInitialLoading(false);
          }
        });
    },
    [],
  );

  useEffect(() => {
    if (!ready || profile === null) return;
    const timer = window.setTimeout(() => {
      loadData(filters);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [ready, profile?.id, filters, loadData]);

  const handleFilterChange = useCallback(
    (key: keyof SessionFilters, value: string) => {
      setFilters((prev) => ({
        ...prev,
        [key]: value,
      }));
    },
    [],
  );

  const handleClearFilters = useCallback(() => {
    setFilters(EMPTY_FILTERS);
  }, []);

  const reload = useCallback(() => {
    loadData(filters);
  }, [filters, loadData]);

  const activeFiltersCount = Object.values(filters).filter(
    (val) => val !== undefined && val !== null && String(val).trim() !== "",
  ).length;

  return {
    filters,
    summary,
    recentSessions,
    athletes,
    initialLoading,
    isRefreshing,
    error,
    athletesError,
    activeFiltersCount,
    handleFilterChange,
    handleClearFilters,
    reload,
  };
}
