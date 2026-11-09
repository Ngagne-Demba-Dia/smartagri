"use client";

import { useTranslations } from "next-intl";

/**
 * Erreur imprévue dans un écran : message générique (aucun détail technique affiché), référence pour le support
 * et bouton pour réessayer. Les erreurs d'API attendues sont gérées dans chaque écran par QueryState.
 */
export default function ModuleError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("errorPage");
  return (
    <section role="alert" aria-labelledby="error-title" className="card mx-auto flex max-w-lg flex-col gap-3">
      <h1 id="error-title" className="text-xl font-bold">
        {t("title")}
      </h1>
      <p className="text-mute">{t("body")}</p>
      {error.digest ? <p className="text-sm text-mute">{t("reference", { digest: error.digest })}</p> : null}
      <button type="button" className="btn-primary min-h-touch self-start" onClick={reset}>
        {t("retry")}
      </button>
    </section>
  );
}
