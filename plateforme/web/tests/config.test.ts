/**
 * Droits d'affichage (lib/roles.ts), modules (lib/modules.ts), CSP (lib/csp.ts),
 * cookies de session (lib/session-cookies.ts) et bascule des simulations (lib/mock-config.ts).
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildCsp, createNonce } from "@/lib/csp";
import { MOCK_BASE, MOCK_SCENARIOS, isMockMode } from "@/lib/mock-config";
import { MOBILE_TABS, MODULES, NAV_GROUPS, moduleBySlug } from "@/lib/modules";
import {
  canAccessRoute,
  canAckAlerts,
  canEditThresholds,
  canGiveFeedback,
  displayRole,
  hasRoleIn,
  visibleNavItems,
} from "@/lib/roles";
import { ACCESS_COOKIE, REFRESH_COOKIE, REFRESH_MAX_AGE_S, cookieOptions } from "@/lib/session-cookies";
import type { Me, Role } from "@/lib/types";

afterEach(() => {
  vi.unstubAllEnvs();
});

const me = (...memberships: Array<[string, Role]>): Me => ({
  id: "u1",
  full_name: null,
  email: null,
  phone: null,
  locale: "fr",
  memberships: memberships.map(([organization_id, role]) => ({
    organization_id,
    organization_name: organization_id,
    organization_kind: "cooperative",
    role,
  })),
});

describe("roles", () => {
  it("l'agronome acquitte les alertes mais ne règle ni seuils ni retours", () => {
    const agronomist = me(["org-a", "agronomist"]);
    expect([
      canAckAlerts(agronomist, "org-a"),
      canEditThresholds(agronomist, "org-a"),
      canGiveFeedback(agronomist, "org-a"),
    ]).toEqual([true, false, false]);
  });

  it("le droit vaut pour l'organisation de l'adhésion seulement", () => {
    const farmer = me(["org-a", "farmer"]);
    expect(canEditThresholds(farmer, "org-a")).toBe(true);
    expect(canEditThresholds(farmer, "org-b")).toBe(false);
  });

  it("sans utilisateur : aucun droit et aucun rôle affiché", () => {
    expect(hasRoleIn(null, "org-a", new Set<Role>(["admin"]))).toBe(false);
    expect(canAckAlerts(undefined, "org-a")).toBe(false);
    expect(displayRole(null)).toBeNull();
    expect(displayRole(me())).toBeNull();
  });

  it("rôle affiché : celui de la première adhésion", () => {
    expect(displayRole(me(["org-a", "coop_manager"], ["org-b", "admin"]))).toBe("coop_manager");
  });

  it("canAccessRoute et visibleNavItems filtrent les routes par rôle (MISSION FRONT-RBAC-02)", () => {
    expect(canAccessRoute("farmer", "tableau")).toBe(true);
    expect(canAccessRoute("farmer", "parcelles")).toBe(true);
    expect(canAccessRoute("farmer", "exploitations")).toBe(false);
    expect(canAccessRoute("farmer", "rapports")).toBe(false);
    expect(canAccessRoute("farmer", "kit")).toBe(false);
    expect(canAccessRoute("farmer", "equipements")).toBe(false);

    expect(canAccessRoute("coop_manager", "exploitations")).toBe(true);
    expect(canAccessRoute("coop_manager", "rapports")).toBe(true);
    expect(canAccessRoute("coop_manager", "equipements")).toBe(true);
    expect(canAccessRoute("coop_manager", "kit")).toBe(false);
    expect(canAccessRoute("coop_manager", "vegetation")).toBe(false);

    expect(canAccessRoute("agronomist", "vegetation")).toBe(true);
    expect(canAccessRoute("agronomist", "previsions")).toBe(true);
    expect(canAccessRoute("agronomist", "kit")).toBe(true);
    expect(canAccessRoute("agronomist", "equipements")).toBe(false);

    expect(canAccessRoute("admin", "kit")).toBe(true);
    expect(canAccessRoute("admin", "equipements")).toBe(true);
    expect(canAccessRoute("admin", "vegetation")).toBe(true);

    const farmerSlugs = visibleNavItems("farmer").flatMap((g) => [
      ...g.extraSlugs,
      ...g.modules.map((m) => m.slug),
      ...g.services.map((s) => s.slug),
    ]);
    expect(farmerSlugs).toContain("tableau");
    expect(farmerSlugs).toContain("communaute");
    expect(farmerSlugs).not.toContain("rapports");
    expect(farmerSlugs).not.toContain("kit");

    const adminSlugs = visibleNavItems("admin").flatMap((g) => [
      ...g.extraSlugs,
      ...g.modules.map((m) => m.slug),
      ...g.services.map((s) => s.slug),
    ]);
    expect(adminSlugs).toContain("rapports");
    expect(adminSlugs).toContain("kit");
    expect(adminSlugs).toContain("equipements");
  });
});

describe("modules", () => {
  it("13 modules d'identifiants et de slugs uniques, chacun dans un groupe connu", () => {
    expect(MODULES).toHaveLength(13);
    expect(new Set(MODULES.map((m) => m.id)).size).toBe(13);
    expect(new Set(MODULES.map((m) => m.slug)).size).toBe(13);
    expect(MODULES.every((m) => NAV_GROUPS.includes(m.group))).toBe(true);
  });

  it("les écrans du jalon v0.1 sont complets", () => {
    for (const slug of ["tableau", "carte", "parcelles", "recommandations", "assistant"]) {
      expect(moduleBySlug(slug).complete).toBe(true);
    }
  });

  it("moduleBySlug lève sur un slug inconnu", () => {
    expect(() => moduleBySlug("inconnu")).toThrow("Module inconnu : inconnu");
  });

  it("barre du bas : accueil, carte, alertes, assistant", () => {
    expect(MOBILE_TABS.map((t) => t.slug)).toEqual(["tableau", "carte", "alertes", "assistant"]);
  });
});

describe("buildCsp et createNonce", () => {
  it("production : nonce, pas d'eval, passage forcé en HTTPS", () => {
    const csp = buildCsp("abc", false);
    expect(csp).toContain("script-src 'self' 'nonce-abc' 'strict-dynamic'; ");
    expect(csp).not.toContain("unsafe-eval");
    expect(csp).not.toContain("unsafe-inline");
    expect(csp.endsWith("upgrade-insecure-requests")).toBe(true);
    expect(csp).toContain("connect-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
  });

  it("développement : eval autorisé, pas de passage forcé en HTTPS", () => {
    const csp = buildCsp("abc", true);
    expect(csp).toContain("'strict-dynamic' 'unsafe-eval'");
    expect(csp).not.toContain("upgrade-insecure-requests");
  });

  it("nonce de 128 bits en base64, différent à chaque appel", () => {
    const a = createNonce();
    expect(a).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    expect(atob(a)).toHaveLength(16);
    expect(createNonce()).not.toBe(a);
  });
});

describe("cookies de session", () => {
  it("noms et durée du jeton de rafraîchissement (30 jours)", () => {
    expect([ACCESS_COOKIE, REFRESH_COOKIE]).toEqual(["sa_at", "sa_rt"]);
    expect(REFRESH_MAX_AGE_S).toBe(2_592_000);
  });

  it("httpOnly et SameSite strict ; secure partout sauf en développement", () => {
    vi.stubEnv("NODE_ENV", "production");
    expect(cookieOptions(60)).toEqual({
      httpOnly: true,
      secure: true,
      sameSite: "strict",
      path: "/",
      maxAge: 60,
    });
    vi.stubEnv("NODE_ENV", "development");
    expect(cookieOptions(60, "/api/auth")).toEqual({
      httpOnly: true,
      secure: false,
      sameSite: "strict",
      path: "/api/auth",
      maxAge: 60,
    });
  });
});

describe("bascule des simulations", () => {
  it("désactivée par défaut, activée par AGRI_MOCK=1 seulement", () => {
    vi.stubEnv("AGRI_MOCK", "");
    expect(isMockMode()).toBe(false);
    vi.stubEnv("AGRI_MOCK", "true");
    expect(isMockMode()).toBe(false);
    vi.stubEnv("AGRI_MOCK", "1");
    expect(isMockMode()).toBe(true);
  });

  it("hôte réservé .invalid et six scénarios de doc 16 §9.5", () => {
    expect(new URL(MOCK_BASE).hostname.endsWith(".invalid")).toBe(true);
    expect(MOCK_SCENARIOS).toEqual(["nominal", "stale", "fallback", "abstention", "error_503", "empty"]);
  });
});
