import type {
  AnalyticsResult,
  Athlete,
  AuthPayload,
  AuthResponse,
  Comparison,
  DashboardSummary,
  IngestContract,
  IngestResult,
  Profile,
  Recommendation,
  ReviewDecision,
  SessionDetail,
  SessionFilters,
  SessionListItem,
} from "@/types/contracts";

/** Error tipado que lanza el cliente ante cualquier fallo de la API. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly errors?: IngestResult["errors"];

  constructor(status: number, detail: string, errors?: IngestResult["errors"]) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.errors = errors;
  }
}

export const ACCESS_KEY = "cadi.access";
export const REFRESH_KEY = "cadi.refresh";
export const PROFILE_KEY = "cadi.profile";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

/** Guarda la sesión completa (tokens + perfil) en localStorage. */
export function saveSession(auth: AuthResponse): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, auth.access);
  window.localStorage.setItem(REFRESH_KEY, auth.refresh);
  window.localStorage.setItem(PROFILE_KEY, JSON.stringify(auth.profile));
}

/** Elimina la sesión local (no revoca el refresh en el servidor). */
export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(PROFILE_KEY);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getStoredProfile(): Profile | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(PROFILE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Profile;
  } catch {
    return null;
  }
}

/** Cierra la sesión local y manda al usuario a /login. */
export function forceLogout(): void {
  clearSession();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  /** Auth obligatoria (por defecto true). */
  auth?: boolean;
  /** Si la petición devuelve 401 se reintenta UNA vez tras purgar la sesión. */
  retried?: boolean;
}

function extractDetail(data: unknown, fallback: string): string {
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (Array.isArray(record.detail)) {
      return record.detail.map(String).join(" ");
    }
    if (typeof record.error === "string") return record.error;
  }
  return fallback;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, auth = true, retried = false } = options;
  const headers: Record<string, string> = { Accept: "application/json" };

  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (!token) {
      forceLogout();
      throw new ApiError(401, "Sesión no válida. Inicia de nuevo.");
    }
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor.");
  }

  if (response.status === 401 && auth) {
    // No existe endpoint de refresh expuesto: se reintenta una vez con la
    // sesión purgada; si vuelve a fallar, se cierra la sesión y se redirige.
    if (!retried) {
      clearSession();
      return request<T>(path, { ...options, retried: true });
    }
    forceLogout();
    throw new ApiError(401, "Sesión expirada. Inicia de nuevo.");
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errors =
      data && typeof data === "object" && Array.isArray((data as { errors?: unknown }).errors)
        ? ((data as { errors: IngestResult["errors"] }).errors)
        : undefined;
    throw new ApiError(
      response.status,
      extractDetail(data, `Error ${response.status} del servidor.`),
      errors,
    );
  }

  return data as T;
}

/** Autenticación (no requiere Bearer). */
export const api = {
  login(payload: AuthPayload): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/login/", {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  register(payload: AuthPayload): Promise<AuthResponse> {
    return request<AuthResponse>("/auth/register/", {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  logout(): Promise<{ detail: string }> {
    const refresh = getStoredRefresh();
    if (!refresh) {
      clearSession();
      return Promise.resolve({ detail: "Sesión cerrada." });
    }
    return request<{ detail: string }>("/auth/logout/", {
      method: "POST",
      body: { refresh },
    }).then((result) => {
      clearSession();
      return result;
    });
  },

  me(): Promise<Profile> {
    return request<Profile>("/auth/me/");
  },

  dashboardSummary(): Promise<DashboardSummary> {
    return request<DashboardSummary>("/dashboard/summary/");
  },

  listSessions(filters: SessionFilters = {}): Promise<SessionListItem[]> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        params.set(key, String(value));
      }
    }
    const query = params.toString();
    return request<SessionListItem[]>(`/sessions/${query ? `?${query}` : ""}`);
  },

  getSession(sessionId: string): Promise<SessionDetail> {
    return request<SessionDetail>(`/sessions/${encodeURIComponent(sessionId)}/`);
  },

  compareSessions(ids: string[]): Promise<Comparison> {
    const query = new URLSearchParams({ ids: ids.join(",") }).toString();
    return request<Comparison>(`/sessions/compare/?${query}`);
  },

  ingestSessions(
    contracts: IngestContract | IngestContract[],
  ): Promise<IngestResult> {
    return request<IngestResult>("/sessions/ingest/", {
      method: "POST",
      body: contracts,
    });
  },

  recommendations(ids: string[]): Promise<AnalyticsResult> {
    const query = new URLSearchParams({ ids: ids.join(",") }).toString();
    return request<AnalyticsResult>(`/analytics/recommendations/?${query}`);
  },

  generateRecommendations(sessionIds: string[]): Promise<AnalyticsResult> {
    return request<AnalyticsResult>("/analytics/recommendations/generate/", {
      method: "POST",
      body: { session_ids: sessionIds },
    });
  },

  reviewRecommendation(
    recommendationId: string,
    decision: ReviewDecision,
    note?: string,
  ): Promise<Recommendation> {
    return request<Recommendation>(
      `/analytics/recommendations/${encodeURIComponent(recommendationId)}/review/`,
      {
        method: "POST",
        body: { decision, note },
      },
    );
  },

  listAthletes(): Promise<Athlete[]> {
    return request<Athlete[]>("/athletes/");
  },
};

function getStoredRefresh(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}
