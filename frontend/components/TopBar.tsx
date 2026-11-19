"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import {
  Activity,
  ArrowUpRight,
  ChartNoAxesCombined,
  Database,
  LayoutDashboard,
  LogOut,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/services/auth";

type NavItem = {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
};

export function TopBar({ children }: { children: ReactNode }) {
  const { profile, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  if (!ready || profile === null || pathname === "/login") return <>{children}</>;

  const isStaff = profile.user_type === "teacher" || profile.user_type === "admin";
  const links: NavItem[] = [
    { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
  ];
  if (isStaff) links.push({ href: "/athletes", label: "Atletas", icon: Users });
  links.push({ href: "/sessions", label: isStaff ? "Pruebas" : "Mis sesiones", icon: Activity });
  links.push({ href: "/sessions/compare", label: "Reportes", icon: ChartNoAxesCombined });
  if (isStaff) links.push({ href: "/ingest", label: "Ingesta", icon: Database });

  const roleLabel = {
    teacher: "Docente",
    student: "Estudiante",
    admin: "Administrador técnico",
  }[profile.user_type];

  const signOut = async () => {
    await logout();
    router.replace("/login");
  };

  const isActive = (href: string) =>
    href === "/dashboard"
      ? pathname === "/" || pathname === "/dashboard"
      : href === "/sessions"
        ? pathname === "/sessions" ||
          (pathname.startsWith("/sessions/") && pathname !== "/sessions/compare")
        : href === "/athletes"
          ? pathname.startsWith("/athletes")
        : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="app-frame">
      <aside className="app-sidebar" aria-label="Navegación principal">
        <Link className="app-brand" href="/dashboard" aria-label="CADI, ir al resumen">
          <span className="app-brand-mark" aria-hidden="true">
            <Activity size={19} strokeWidth={2.5} />
          </span>
          <span className="app-brand-copy">
            <strong>CADI</strong>
            <small>FASE II · INFORMACIÓN DEPORTIVA</small>
          </span>
          <ArrowUpRight className="app-brand-arrow" size={15} aria-hidden="true" />
        </Link>

        <div className="sidebar-section-label">OPERACIONES DE PISTA</div>
        <nav className="sidebar-nav">
          {links.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                className={`sidebar-link${active ? " active" : ""}`}
                href={href}
                key={href}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={18} strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" />
                <span>{label}</span>
                {active && <span className="sidebar-active-mark" aria-hidden="true" />}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-source-note">
            <span className="status-dot" aria-hidden="true" />
            <span>
              <strong>Fuente versionada</strong>
              <small>Datos con procedencia registrada</small>
            </span>
          </div>
          <div className="sidebar-user">
            <span className="user-avatar" aria-hidden="true">
              {(profile.first_name || profile.email).slice(0, 1).toUpperCase()}
            </span>
            <span className="sidebar-user-copy">
              <strong>{profile.first_name || profile.email}</strong>
              <small>{roleLabel}</small>
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="sidebar-logout"
              type="button"
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
              onClick={() => void signOut()}
            >
              <LogOut size={17} aria-hidden="true" />
            </Button>
          </div>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="workspace-header">
          <div className="workspace-breadcrumb">
            <span className="breadcrumb-overline">CENTRO ACADÉMICO DEPORTIVO</span>
            <span className="breadcrumb-divider" aria-hidden="true">/</span>
            <span className="breadcrumb-current">
              {links.find(({ href }) => isActive(href))?.label ?? "Sesión"}
            </span>
          </div>
          <div className="workspace-header-right">
            <span className="role-pill">{roleLabel}</span>
            <span className="header-initial" aria-hidden="true">
              {(profile.first_name || profile.email).slice(0, 1).toUpperCase()}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="mobile-logout"
              type="button"
              aria-label="Cerrar sesión"
              onClick={() => void signOut()}
            >
              <LogOut size={18} aria-hidden="true" />
            </Button>
          </div>
        </header>

        <main className="app-content">{children}</main>
      </div>

      <nav className="mobile-nav" aria-label="Navegación móvil">
        {links.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={`mobile-nav-link${active ? " active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={20} strokeWidth={active ? 2.3 : 1.8} aria-hidden="true" />
              <span>{label}</span>
            </Link>
          );
        })}
        {isStaff && (
          <Link
            href="/ingest"
            className={`mobile-nav-link${pathname.startsWith("/ingest") ? " active" : ""}`}
            aria-current={pathname.startsWith("/ingest") ? "page" : undefined}
          >
            <Database size={20} aria-hidden="true" />
            <span>Ingesta</span>
          </Link>
        )}
      </nav>
    </div>
  );
}
