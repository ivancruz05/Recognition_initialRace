import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AuthProvider } from "./AuthProvider";
import { TopBar } from "@/components/TopBar";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "CADI · Fase II",
  description:
    "Monitoreo de velocidad, zancada, cadencia y postura en atletas iniciales.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={cn("font-sans", geist.variable)}>
      <body>
        <AuthProvider>
          <TopBar />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
