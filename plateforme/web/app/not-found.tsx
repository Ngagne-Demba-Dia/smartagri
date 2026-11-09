import { getLocale, getTranslations } from "next-intl/server";
import Link from "next/link";

import { DEFAULT_LOCALE, isLocale } from "@/i18n/routing";
import { HOME_SLUG, localePath } from "@/lib/nav";

/** Page introuvable : rendue sous le layout racine seul (pas de session requise, pas de données). */
export default async function NotFound() {
  const t = await getTranslations("notFound");
  const current = await getLocale();
  const locale = isLocale(current) ? current : DEFAULT_LOCALE;
  return (
    <main id="contenu" className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 text-center">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p className="max-w-md text-mute">{t("body")}</p>
      <Link href={localePath(locale, `/${HOME_SLUG}`)} className="btn-primary min-h-touch">
        {t("home")}
      </Link>
    </main>
  );
}
