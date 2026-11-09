"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import { useId } from "react";

import { LOCALES, isLocale } from "@/i18n/routing";
import { stripLocale } from "@/lib/nav";

/** Change la langue en gardant la page courante ; rechargement complet pour relire les messages côté serveur. */
export function LocaleSwitcher() {
  const t = useTranslations("locale");
  const locale = useLocale();
  const pathname = usePathname();
  const id = useId();

  const change = (next: string) => {
    if (!isLocale(next) || next === locale) return;
    window.location.assign(`/${next}${stripLocale(pathname)}${window.location.search}`);
  };

  return (
    <div className="flex items-center gap-1">
      <label htmlFor={id} className="sr-only">
        {t("label")}
      </label>
      <select id={id} className="field-input w-auto" value={locale} onChange={(e) => change(e.target.value)}>
        {LOCALES.map((l) => (
          <option key={l} value={l} lang={l}>
            {t(l)}
          </option>
        ))}
      </select>
    </div>
  );
}
