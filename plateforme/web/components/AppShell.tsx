"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { useMe } from "@/hooks/places";
import type { Locale } from "@/i18n/routing";
import { api } from "@/lib/client";
import { LOGIN_SLUG, localePath } from "@/lib/nav";
import { canAccessRoute, displayRole } from "@/lib/roles";
import { sceneForPath } from "@/lib/scene";

import { BottomBar } from "./BottomBar";
import { Brand } from "./Brand";
import { Icon } from "./Icon";
import { LocaleSwitcher } from "./LocaleSwitcher";
import { Scene } from "./Scene";
import { Sidebar } from "./Sidebar";
import { SyncBanner } from "./SyncBanner";
import { ThemeToggle } from "./ThemeToggle";
import { TranslationBanner } from "./TranslationBanner";

/** Tiroir de menu sur téléphone : <dialog> natif (piège du focus, Échap, arrière-plan inerte). */
function MenuDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useTranslations("common");
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-label={t("menu")}
      className="m-0 h-full max-h-none w-80 max-w-[85vw] overflow-y-auto border-r border-glass-edge bg-[var(--glass-strong)] p-0 text-ink backdrop-blur-2xl backdrop:bg-black/50 backdrop:backdrop-blur-sm"
    >
      <div className="flex items-center justify-between gap-2 p-3">
        <Brand name={t("appName")} />
        <button type="button" className="btn-secondary" onClick={onClose}>
          <Icon name="close" size={18} />
          {t("closeMenu")}
        </button>
      </div>
      <Sidebar />
    </dialog>
  );
}

/**
 * Coque des pages connectées : navigation, en-tête (rôle, langue, déconnexion), bandeaux d'état.
 * `banner` : bandeau supplémentaire sous l'en-tête (bandeau du mode simulé, posé par le layout serveur).
 */
export function AppShell({ children, banner }: { children: ReactNode; banner?: ReactNode }) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const me = useMe();
  const role = displayRole(me.data);
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutFailed, setLogoutFailed] = useState(false);

  // Le tiroir se ferme dès qu'on change de page.
  useEffect(() => setMenuOpen(false), [pathname]);

  const logout = async () => {
    setLoggingOut(true);
    setLogoutFailed(false);
    try {
      await api.post("/auth/logout");
    } catch {
      setLogoutFailed(true);
      setLoggingOut(false);
      return;
    }
    queryClient.clear();
    window.location.assign(localePath(locale, `/${LOGIN_SLUG}`));
  };

  const scene = sceneForPath(pathname);

  return (
    <div data-scene={scene} className="relative isolate min-h-screen md:flex">
      <Scene scene={scene} />
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-30 focus:rounded-btn focus:bg-card focus:p-3"
      >
        {t("skipToContent")}
      </a>
      <aside className="hidden md:block md:w-72 md:shrink-0 md:p-3 md:pr-0">
        <div className="glass glass-strong sticky top-3 flex max-h-[calc(100vh-1.5rem)] flex-col overflow-y-auto">
          <div className="px-4 pb-1 pt-4">
            <Brand name={t("appName")} />
          </div>
          <Sidebar />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="glass glass-strong sticky top-3 z-20 mx-3 mt-3 flex flex-wrap items-center justify-between gap-2 px-4 py-2 md:mx-6">
          <span className="md:hidden">
            <Brand name={t("appName")} />
          </span>
          <div className="ml-auto flex items-center gap-2">
            {role ? (
              <span className="chip hidden whitespace-nowrap text-sm text-mute lg:inline-flex">
                {t("connectedAs", { role: t(`roles.${role}`) })}
              </span>
            ) : null}
            <ThemeToggle />
            <LocaleSwitcher />
            <button
              type="button"
              className="btn-secondary whitespace-nowrap"
              onClick={logout}
              disabled={loggingOut}
            >
              <Icon name="logout" />
              <span className="sr-only sm:not-sr-only sm:whitespace-nowrap">{t("logout")}</span>
            </button>
          </div>
        </header>
        {logoutFailed ? (
          <p role="alert" className="bg-bad-bg px-4 py-2 text-sm font-semibold text-bad-ink">
            {t("logoutFailed")}
          </p>
        ) : null}
        {banner}
        <SyncBanner />
        <TranslationBanner />
        <main
          id="contenu"
          tabIndex={-1}
          className="mx-auto w-full max-w-7xl flex-1 px-4 pb-28 pt-5 md:px-6 md:pb-10"
        >
          {role && !canAccessRoute(role, pathname) ? (
            <section
              data-testid="rbac-forbidden"
              aria-labelledby="rbac-forbidden-title"
              className="card reveal mx-auto my-8 max-w-2xl p-6"
            >
              <p className="eyebrow">{t("forbiddenEyebrow")}</p>
              <h1 id="rbac-forbidden-title" className="mt-1 text-2xl font-bold text-ink">
                {t("forbiddenTitle")}
              </h1>
              <p className="mt-2 text-sm text-mute">
                {t("forbiddenBody", { role: t(`roles.${role}`) })}
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link href={localePath(locale, "/tableau")} className="btn-primary">
                  {t("forbiddenBack")}
                </Link>
              </div>
            </section>
          ) : (
            children
          )}
        </main>
      </div>
      <BottomBar onMenu={() => setMenuOpen(true)} menuOpen={menuOpen} />
      <MenuDrawer open={menuOpen} onClose={() => setMenuOpen(false)} />
    </div>
  );
}
