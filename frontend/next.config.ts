import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Next 15 usa una sola carpeta por defecto. Aislar dev de build evita que
  // `next build` reemplace chunks que un `next dev` aún tiene cargados.
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
};

export default nextConfig;
