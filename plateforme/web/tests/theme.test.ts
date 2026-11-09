import { describe, expect, it } from "vitest";

import { otherTheme, parseTheme, resolveTheme, THEME_COOKIE, themeCookie } from "@/lib/theme";

describe("thème", () => {
  it("n'accepte que light et dark", () => {
    expect(parseTheme("dark")).toBe("dark");
    expect(parseTheme("light")).toBe("light");
    expect(parseTheme("system")).toBeNull();
    expect(parseTheme("")).toBeNull();
    expect(parseTheme(undefined)).toBeNull();
    expect(parseTheme(null)).toBeNull();
  });

  it("bascule vers l'autre thème", () => {
    expect(otherTheme("dark")).toBe("light");
    expect(otherTheme("light")).toBe("dark");
  });

  it("écrit un cookie d'un an, SameSite=Lax, sur tout le site", () => {
    const cookie = themeCookie("dark");
    expect(cookie.startsWith(`${THEME_COOKIE}=dark;`)).toBe(true);
    expect(cookie).toContain("path=/");
    expect(cookie).toContain("max-age=31536000");
    expect(cookie).toContain("SameSite=Lax");
  });
});

describe("thème effectif", () => {
  it("le choix explicite l'emporte sur le système", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("sans choix, suit le système", () => {
    expect(resolveTheme(null, true)).toBe("dark");
    expect(resolveTheme(undefined, false)).toBe("light");
    expect(resolveTheme("inconnu", true)).toBe("dark");
  });
});
