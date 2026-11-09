/**
 * Chemins internes (lib/nav.ts) et langues (i18n/routing.ts) : `safeNext` refuse toute redirection ouverte,
 * `negotiateLocale` lit Accept-Language avec ses poids q.
 */
import { describe, expect, it } from "vitest";

import { DEFAULT_LOCALE, LOCALES, isLocale, negotiateLocale } from "@/i18n/routing";
import { firstParam, localeFromPathname, localePath, safeNext, stripLocale } from "@/lib/nav";

describe("localePath, stripLocale et localeFromPathname", () => {
  it("préfixe par la langue, avec ou sans barre initiale", () => {
    expect(localePath("fr", "/carte")).toBe("/fr/carte");
    expect(localePath("wo", "carte")).toBe("/wo/carte");
  });

  it("retire le préfixe de langue en gardant la requête", () => {
    expect(stripLocale("/fr/parcelles?x=1")).toBe("/parcelles?x=1");
    expect(stripLocale("/fr")).toBe("/");
    expect(stripLocale("/parcelles")).toBe("/parcelles");
  });

  it("lit la langue du chemin ; langue par défaut sinon", () => {
    expect(localeFromPathname("/ff/tableau")).toBe("ff");
    expect(localeFromPathname("/en/tableau")).toBe(DEFAULT_LOCALE);
    expect(localeFromPathname("/")).toBe(DEFAULT_LOCALE);
  });
});

describe("safeNext", () => {
  const home = "/fr/tableau";

  it.each([
    ["absent", null],
    ["vide", ""],
    ["absolu", "https://exemple.invalid/fr/tableau"],
    ["schéma javascript", "javascript:alert(1)"],
    ["protocole relatif", "//exemple.invalid"],
    ["antislash", "/\\exemple.invalid"],
    ["caractère de contrôle", "/carte\u0000"],
    ["tabulation", "/car\tte"],
    ["retour à la connexion", "/login"],
    ["connexion préfixée", "/wo/login?next=/carte"],
    ["sous-chemin de connexion", "/fr/login/reset"],
  ])("refuse %s → accueil", (_label, next) => {
    expect(safeNext(next, "fr")).toBe(home);
  });

  it("préfixe un chemin interne par la langue, requête et ancre comprises", () => {
    expect(safeNext("/carte?mode=ndvi#f1", "fr")).toBe("/fr/carte?mode=ndvi#f1");
  });

  it("ne préfixe pas deux fois un chemin déjà préfixé", () => {
    expect(safeNext("/wo/parcelles", "fr")).toBe("/wo/parcelles");
  });

  it("accepte un chemin qui commence seulement par « login »", () => {
    expect(safeNext("/loginx", "ff")).toBe("/ff/loginx");
  });
});

describe("firstParam", () => {
  it("première valeur non vide ; null sinon", () => {
    expect(firstParam("a")).toBe("a");
    expect(firstParam(["b", "c"])).toBe("b");
    expect(firstParam([])).toBeNull();
    expect(firstParam("")).toBeNull();
    expect(firstParam(undefined)).toBeNull();
  });
});

describe("langues (i18n/routing)", () => {
  it("fr par défaut, puis wo et ff", () => {
    expect(LOCALES).toEqual(["fr", "wo", "ff"]);
    expect(isLocale("wo")).toBe(true);
    expect(isLocale("en")).toBe(false);
    expect(isLocale(null)).toBe(false);
    expect(isLocale(undefined)).toBe(false);
  });

  it.each([
    [null, "fr"],
    ["", "fr"],
    ["en-US,en;q=0.9", "fr"],
    ["wo-SN", "wo"],
    ["en;q=0.9,ff;q=0.8,wo;q=0.5", "ff"],
    ["fr;q=0.3, WO;q=0.7", "wo"],
    ["wo;q=abc, ff;q=0.1", "ff"],
    ["*;q=0.5", "fr"],
  ])("Accept-Language %j → %s", (header, expected) => {
    expect(negotiateLocale(header)).toBe(expected);
  });
});
