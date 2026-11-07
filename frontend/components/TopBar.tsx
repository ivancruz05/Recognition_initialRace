"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { isStaff, useAuth } from "@/services/auth";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const { profile, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  if (!ready || profile === null || pathname === "/login") return null;

  const handleLogout = () => {
    void logout().then(() => router.replace("/login"));
  };

  const links: { href: string; label: string }[] = [
    { href: "/dashboard", label: "Resumen" },
    { href: "/sessions", label: "Sesiones" },
  ];
  if (isStaff(profile)) {
    links.push({ href: "/ingest", label: "Ingesta" });
  }

  const roleLabel = {
    teacher: "Docente",
    student: "Estudiante",
    admin: "Administrador técnico",
  }[profile.user_type];

  return (
    <header className="topbar">
      <Link href="/dashboard" className="logo">
        CADI · Fase II
      </Link>
      <nav aria-label="Navegación principal">
        {links.map((link) => {
          const active =
            link.href === "/dashboard"
              ? pathname === "/dashboard" || pathname === "/"
              : pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={active ? "active" : undefined}
              aria-current={active ? "page" : undefined}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
      <span className="spacer" />
      <span className="whoami">
        {profile.first_name || profile.email}
        <span className="role-label">{roleLabel}</span>
      </span>
      <Button type="button" variant="outline" className="btn secondary" onClick={handleLogout}>
        Salir
      </Button>
    </header>
  );
}
