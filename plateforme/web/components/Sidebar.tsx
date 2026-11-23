"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useMe } from "@/hooks/places";
import type { Locale } from "@/i18n/routing";
import { localePath } from "@/lib/nav";
import { displayRole, visibleNavItems } from "@/lib/roles";

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

/** Navigation par groupes filtrée selon le rôle actif (visibleNavItems, MISSION FRONT-RBAC-02). */
export function Sidebar() {
  const t = useTranslations("nav");
  const tm = useTranslations("modules");
  const tv = useTranslations("versions");
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const me = useMe();
  const role = displayRole(me.data);
  const groups = visibleNavItems(role);
  const isActive = (slug: string) => {
    const base = localePath(locale, `/${slug}`);
    return pathname === base || pathname.startsWith(`${base}/`);
  };

  return (
    <nav aria-label={t("main")} className="flex flex-col gap-5 p-3">
      {groups.map(({ group, extraSlugs, modules, services }) => (
        <div key={group} className="flex flex-col gap-1">
          <h2 className="px-3 text-xs font-semibold uppercase tracking-wide text-mute">
            {t(`groups.${group}`)}
          </h2>
          <ul className="flex flex-col gap-0.5">
            {extraSlugs.map((slug) => (
              <li key={slug}>
                <NavLink
                  href={localePath(locale, `/${slug}`)}
                  icon={slug === "alertes" ? "bell" : "chat"}
                  label={slug === "alertes" ? t("alerts") : t("community")}
                  active={isActive(slug)}
                />
              </li>
            ))}
            {modules.map((m) => (
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
            {services.map((s) => (
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
