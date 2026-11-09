"use client";

import { useLocale, useTranslations } from "next-intl";

import { UNTRANSLATED_LOCALES, isLocale } from "@/i18n/routing";

import { Icon } from "./Icon";

/** Wolof et pulaar : pas de texte inventé, l'interface reste en français et le dit (doc 10 §6). */
export function TranslationBanner() {
  const t = useTranslations("translation");
  const locale = useLocale();
  if (!isLocale(locale) || !UNTRANSLATED_LOCALES.has(locale)) return null;
  return (
    <p className="flex items-center gap-2 bg-bg px-4 py-1.5 text-sm text-ink">
      <Icon name="info" size={16} />
      {t("notice")}
    </p>
  );
}
