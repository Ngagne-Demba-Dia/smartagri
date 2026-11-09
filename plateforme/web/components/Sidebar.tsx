"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Locale } from "@/i18n/routing";
import { MODULES, NAV_GROUPS } from "@/lib/modules";
import { localePath } from "@/lib/nav";
import { SERVICE_SCREENS } from "@/lib/service-screens";

import { Icon, type IconName } from "./Icon";

function NavLink({
  href,
  icon,
  label,
  tag,
  active,
}: {
  href: string;
  icon: IconName;
  label: string;
  tag?: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`relative flex min-h-touch items-center gap-3 rounded-btn px-3 transition-colors ${
        active ? "nav-active font-semibold text-ink" : "text-ink hover:bg-surface"
      }`}
    >
      {active ? <span aria-hidden="true" className="absolute inset-y-2 left-0 w-1 rounded-r bg-accent shadow-[0_0_12px_var(--accent)]" /> : null}
      <Icon name={icon} />
      <span className="flex-1">{label}</span>
      {tag ? <span className="rounded-full border border-line px-2 text-xs text-mute">{tag}</span> : null}
    </Link>
  );
}

/** Navigation par groupes (doc 10 §3.1) ; les modules hors MVP portent leur étiquette de version. */
export function Sidebar() {
  const t = useTranslations("nav");
  const tm = useTranslations("modules");
  const tv = useTranslations("versions");
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const isActive = (slug: string) => {
    const base = localePath(locale, `/${slug}`);
    return pathname === base || pathname.startsWith(`${base}/`);
  };

  return (
    <nav aria-label={t("main")} className="flex flex-col gap-5 p-3">
      {NAV_GROUPS.map((group) => (
        <div key={group} className="flex flex-col gap-1">
          <h2 className="px-3 text-xs font-semibold uppercase tracking-wide text-mute">
            {t(`groups.${group}`)}
          </h2>
          <ul className="flex flex-col gap-0.5">
            {group === "pilotage" ? (
              <li>
                <NavLink
                  href={localePath(locale, "/alertes")}
                  icon="bell"
                  label={t("alerts")}
                  active={isActive("alertes")}
                />
              </li>
            ) : null}
            {MODULES.filter((m) => m.group === group).map((m) => (
              <li key={m.slug}>
                <NavLink
                  href={localePath(locale, `/${m.slug}`)}
                  icon={m.icon}
                  label={tm(m.key)}
                  tag={m.version === "MVP" ? undefined : tv(m.version)}
                  active={isActive(m.slug)}
                />
              </li>
            ))}
            {SERVICE_SCREENS.filter((s) => s.group === group).map((s) => (
              <li key={s.slug}>
                <NavLink
                  href={localePath(locale, `/${s.slug}`)}
                  icon={s.icon}
                  label={tm(s.key)}
                  tag={s.version === "MVP" ? undefined : tv(s.version)}
                  active={isActive(s.slug)}
                />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
