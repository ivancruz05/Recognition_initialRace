import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { AuthProvider } from "./AuthProvider";
import { TopBar } from "@/components/TopBar";
import { Barlow_Condensed, IBM_Plex_Mono, Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});
const display = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-barlow",
  display: "swap",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CADI · Fase II",
  description:
    "Monitoreo de velocidad, zancada, cadencia y postura en atletas iniciales.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={`${inter.variable} ${display.variable} ${mono.variable}`}>
      <body>
        <AuthProvider>
          <TopBar>{children}</TopBar>
        </AuthProvider>
      </body>
    </html>
  );
}
