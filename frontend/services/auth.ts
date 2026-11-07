"use client";

import { createContext, useContext, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Profile } from "@/types/contracts";
import { ApiError } from "@/services/apiClient";

export interface AuthContextValue {
  /** Perfil del usuario autenticado, o null si no hay sesión. */
  profile: Profile | null;
  /** true cuando la sesión inicial ya se resolvió (aunque sea nula). */
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  }
  return context;
}

/**
 * Hook de protección de rutas: lee la sesión, redirige a /login si no existe
 * y devuelve el perfil cuando la comprobación inicial termina.
 */
export function useRequireAuth(): { profile: Profile | null; ready: boolean } {
  const { profile, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && profile === null) {
      router.replace("/login");
    }
  }, [ready, profile, router]);

  return { profile, ready };
}

/** teacher y admin pueden consultar atletas e ingerir sesiones. */
export function isStaff(profile: Profile | null): boolean {
  return profile?.user_type === "teacher" || profile?.user_type === "admin";
}
