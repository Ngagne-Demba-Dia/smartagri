import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { ModuleVersion } from "@/lib/modules";

/**
 * En-tête commun d'un module : bandeau photo (recadré selon l'écran via `data-scene` posé par la coque),
 * titre, étiquette de version (hors MVP), actions éventuelles. Image simple <img> : la CSP à nonce interdit
 * l'attribut style que next/image ajouterait. alt="" : décorative.
 */
export function ModuleShell({
  title,
  description,
  version,
  actions,
  children,
}: {
  title: string;
  /** Une phrase sous le titre : à quoi sert l'écran. */
  description?: string;
  version?: ModuleVersion;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("versions");
  return (
    <section className="flex flex-col gap-5" aria-labelledby="module-title">
      <header className="banner reveal">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/img/champ-hero.webp" alt="" width={1280} height={855} className="banner-img" />
        <div className="banner-scrim" />
        <div className="flex min-h-36 flex-wrap items-end justify-between gap-4 px-5 py-6 text-white sm:min-h-44 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 id="module-title" className="text-2xl font-bold tracking-tight sm:text-4xl">
                {title}
              </h1>
              {version && version !== "MVP" ? (
                <span className="rounded-full border border-white/50 bg-white/15 px-2 py-0.5 text-sm text-white backdrop-blur">
                  {t(version)}
                </span>
              ) : null}
            </div>
            {description ? <p className="max-w-prose text-white sm:text-lg">{description}</p> : null}
          </div>
          {actions}
        </div>
      </header>
      {children}
    </section>
  );
}
