"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Locale } from "@/i18n/routing";
import { MOBILE_TABS } from "@/lib/modules";
import { localePath } from "@/lib/nav";

import { Icon } from "./Icon";

const ITEM = "flex min-h-touch flex-1 flex-col items-center justify-center gap-0.5 text-xs";

/** Barre du bas sur téléphone : quatre accès directs puis « Menu » (doc 10 §3.1). */
export function BottomBar({ onMenu, menuOpen }: { onMenu: () => void; menuOpen: boolean }) {
  const t = useTranslations("nav");
  const tc = useTranslations("common");
  const locale = useLocale() as Locale;
  const pathname = usePathname();

  return (
    <nav
      aria-label={t("quick")}
      className="glass glass-strong fixed inset-x-3 bottom-3 z-20 overflow-hidden !rounded-[26px] md:hidden"
    >
      <ul className="flex">
        {MOBILE_TABS.map((tab) => {
          const href = localePath(locale, `/${tab.slug}`);
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={tab.slug} className="flex flex-1">
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`${ITEM} ${active ? "nav-active-bottom font-semibold text-g" : "text-mute"}`}
              >
                <Icon name={tab.icon} />
                {t(`tabs.${tab.key}`)}
              </Link>
            </li>
          );
        })}
        <li className="flex flex-1">
          <button
            type="button"
            className={`${ITEM} text-mute`}
            onClick={onMenu}
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
          >
            <Icon name="menu" />
            {tc("menu")}
          </button>
        </li>
      </ul>
    </nav>
  );
}
