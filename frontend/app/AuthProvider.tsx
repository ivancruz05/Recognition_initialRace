"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Profile } from "@/types/contracts";
import {
  ApiError,
  api,
  clearSession,
  getAccessToken,
  getStoredProfile,
  saveSession,
} from "@/services/apiClient";
import { AuthContext, type AuthContextValue } from "@/services/auth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [ready, setReady] = useState(false);

  // Al montar: recupera la sesión local y la valida contra /auth/me/.
  useEffect(() => {
    let cancelled = false;

    const stored = getStoredProfile();
    const token = getAccessToken();

    if (!stored || !token) {
      clearSession();
      setReady(true);
      return;
    }

    setProfile(stored);
    api
      .me()
      .then((fresh) => {
        if (cancelled) return;
        setProfile(fresh);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        // 401 ya redirige y limpia dentro del cliente; ante fallos de red se
        // conserva el perfil guardado para no expulsar al usuario sin motivo.
        if (error instanceof ApiError && error.status !== 0) {
          clearSession();
          setProfile(null);
        }
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const session = await api.login({ email, password });
    saveSession(session);
    setProfile(session.profile);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const session = await api.register({ email, password });
    saveSession(session);
    setProfile(session.profile);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Aunque falle el revoke en el servidor, se cierra la sesión local.
      clearSession();
    }
    setProfile(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ profile, ready, login, register, logout }),
    [profile, ready, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
