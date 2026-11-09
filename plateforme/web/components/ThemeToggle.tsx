"use client";

import { useTranslations } from "next-intl";
import { useCallback, useSyncExternalStore } from "react";

import { otherTheme, resolveTheme, themeCookie, type Theme } from "@/lib/theme";

import { Icon } from "./Icon";

const DARK_QUERY = "(prefers-color-scheme: dark)";

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(DARK_QUERY);
  media.addEventListener("change", onChange);
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => {
    media.removeEventListener("change", onChange);
    observer.disconnect();
  };
}

const currentTheme = (): Theme =>
  resolveTheme(document.documentElement.dataset.theme, window.matchMedia(DARK_QUERY).matches);

/** Bascule clair / sombre. Le choix est un cookie lu par le layout serveur (jamais localStorage, doc 10 §7). */
export function ThemeToggle() {
  const t = useTranslations("common");
  const theme = useSyncExternalStore(subscribe, currentTheme, () => "light" as Theme);
  const toggle = useCallback(() => {
    const next = otherTheme(currentTheme());
    document.documentElement.dataset.theme = next;
    document.cookie = themeCookie(next);
  }, []);

  return (
    <button
      type="button"
      className="btn-secondary px-0"
      onClick={toggle}
      aria-label={theme === "dark" ? t("themeToLight") : t("themeToDark")}
    >
      <Icon name={theme === "dark" ? "sun" : "moon"} />
    </button>
  );
}
