import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/**
 * En-têtes de sécurité communs à toutes les réponses.
 * La CSP des pages est posée par middleware.ts (nonce par requête, voir lib/csp.ts) ;
 * les routes /api/* ne servent que du JSON ou du CSV : CSP « default-src 'none' ».
 * Ne pas ajouter ici de CSP sur les pages : deux CSP se cumulent et la seconde bloquerait le nonce.
 */
const commonHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(self), microphone=(self), geolocation=(self), payment=(), usb=(), interest-cohort=()",
  },
];

const apiHeaders = [
  { key: "Content-Security-Policy", value: "default-src 'none'; frame-ancestors 'none'; base-uri 'none'" },
  { key: "Cache-Control", value: "no-store" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  productionBrowserSourceMaps: false,
  images: { unoptimized: true },
  // Simulations (AGRI_MOCK=1) : msw est chargé tel quel depuis node_modules, jamais empaqueté.
  serverExternalPackages: ["msw"],
  async headers() {
    return [
      { source: "/:path*", headers: commonHeaders },
      { source: "/api/:path*", headers: apiHeaders },
    ];
  },
};

export default withNextIntl(nextConfig);
