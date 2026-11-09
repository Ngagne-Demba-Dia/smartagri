import "./globals.css";

import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { cookies } from "next/headers";
import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { DEFAULT_LOCALE, UNTRANSLATED_LOCALES, isLocale } from "@/i18n/routing";
import { parseTheme, THEME_COOKIE } from "@/lib/theme";

export const metadata: Metadata = {
  title: { default: "SmartAgri92", template: "%s · SmartAgri92" },
  applicationName: "SmartAgri92",
  description: "Pilotage de l'irrigation et des cultures : kits de terrain, météo, recommandations.",
  robots: { index: false, follow: false },
  referrer: "strict-origin-when-cross-origin",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light dark",
};

/**
 * Inter, hébergée avec l'application (CSP font-src 'self', aucun appel à un service de polices).
 * Deux sous-ensembles à graisse variable : le latin de base, puis le latin étendu (caractères
 * pulaar, ɓ ɗ ŋ ñ…), que le navigateur ne télécharge que si un caractère manque au premier (repli par caractère).
 */
const interLatin = localFont({
  src: "./fonts/inter-latin-wght-normal.woff2",
  variable: "--font-inter",
  weight: "100 900",
  display: "swap",
});
const interLatinExt = localFont({
  src: "./fonts/inter-latin-ext-wght-normal.woff2",
  variable: "--font-inter-ext",
  weight: "100 900",
  display: "swap",
});

/**
 * Layout racine : document HTML et feuille de style. La langue vient de l'en-tête posé par le middleware.
 * Wolof et pulaar retombent sur le texte français tant qu'ils ne sont pas traduits : lang="fr" dans ce cas,
 * pour que les lecteurs d'écran prononcent le texte avec la bonne voix.
 * Le thème choisi (cookie) est posé côté serveur : pas de flash clair avant le thème sombre.
 */
export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const lang = isLocale(locale) && !UNTRANSLATED_LOCALES.has(locale) ? locale : DEFAULT_LOCALE;
  const theme = parseTheme((await cookies()).get(THEME_COOKIE)?.value);
  return (
    <html
      lang={lang}
      data-theme={theme ?? undefined}
      className={`${interLatin.variable} ${interLatinExt.variable}`}
    >
      <body className="bg-bg text-ink antialiased">{children}</body>
    </html>
  );
}
