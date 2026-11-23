/**
 * Droits d'affichage et de navigation côté interface, alignés sur backend/app/core/constants.py
 * et sur l'audit ROLE_BASED_ACCESS_AUDIT.md (MISSION FRONT-RBAC-02).
 * Ils ne servent qu'à adapter l'expérience par rôle et masquer les actions impossibles : l'API reste seule juge (403 sinon).
 */
import { MODULES, NAV_GROUPS, type ModuleDef, type NavGroup } from "./modules";
import { SERVICE_SCREENS, type ServiceScreenDef } from "./service-screens";
import type { Me, Role } from "./types";

export const THRESHOLD_WRITERS: ReadonlySet<Role> = new Set<Role>(["farmer", "coop_manager", "admin"]);
export const FEEDBACK_WRITERS: ReadonlySet<Role> = new Set<Role>(["farmer", "coop_manager", "admin"]);
export const ALERT_ACKERS: ReadonlySet<Role> = new Set<Role>(["farmer", "coop_manager", "agronomist", "admin"]);

/** Routes masquées par rôle dans la navigation conformément à ROLE_BASED_ACCESS_AUDIT.md §6.3. */
export const HIDDEN_ROUTES_BY_ROLE: Readonly<Record<Role, ReadonlySet<string>>> = {
  farmer: new Set(["exploitations", "rapports", "kit", "vegetation", "previsions", "equipements"]),
  coop_manager: new Set(["kit", "vegetation", "previsions"]),
  agronomist: new Set(["equipements"]),
  admin: new Set(),
};

export function hasRoleIn(me: Me | null | undefined, organizationId: string, allowed: ReadonlySet<Role>): boolean {
  if (!me) return false;
  return me.memberships.some((m) => m.organization_id === organizationId && allowed.has(m.role));
}

export function canEditThresholds(me: Me | null | undefined, organizationId: string): boolean {
  return hasRoleIn(me, organizationId, THRESHOLD_WRITERS);
}

export function canGiveFeedback(me: Me | null | undefined, organizationId: string): boolean {
  return hasRoleIn(me, organizationId, FEEDBACK_WRITERS);
}

export function canAckAlerts(me: Me | null | undefined, organizationId: string): boolean {
  return hasRoleIn(me, organizationId, ALERT_ACKERS);
}

/** Rôle affiché dans l'en-tête (le premier rôle trouvé) : l'interface nomme des rôles, jamais des personnes. */
export function displayRole(me: Me | null | undefined): Role | null {
  return me?.memberships[0]?.role ?? null;
}

/**
 * Vrai si le rôle est autorisé à accéder au module/écran identifié par son slug ou chemin.
 * Tant que le profil n'est pas chargé (`role === null`), renvoie true pour ne pas bloquer l'hydratation.
 */
export function canAccessRoute(role: Role | null | undefined, slugOrPath: string): boolean {
  if (!role) return true;
  const cleaned = slugOrPath.replace(/^\/+/, "");
  const parts = cleaned.split(/[/?#]/).filter(Boolean);
  const slug = parts[0] === "fr" || parts[0] === "wo" || parts[0] === "ff" ? (parts[1] ?? "") : (parts[0] ?? "");
  if (!slug || slug === "login") return true;
  return !HIDDEN_ROUTES_BY_ROLE[role].has(slug);
}

export type ExtraNavSlug = "alertes" | "communaute";

export interface VisibleNavGroup {
  group: NavGroup;
  extraSlugs: readonly ExtraNavSlug[];
  modules: readonly ModuleDef[];
  services: readonly ServiceScreenDef[];
}

/** Retourne les groupes et entrées de menu visibles pour le rôle donné (ROLE_BASED_ACCESS_AUDIT.md §5). */
export function visibleNavItems(role: Role | null | undefined): VisibleNavGroup[] {
  return NAV_GROUPS.map((group) => {
    const extraSlugs: readonly ExtraNavSlug[] =
      group === "pilotage"
        ? (["alertes", "communaute"] as const).filter((slug) => canAccessRoute(role, slug))
        : [];
    const modules = MODULES.filter((m) => m.group === group && canAccessRoute(role, m.slug));
    const services = SERVICE_SCREENS.filter((s) => s.group === group && canAccessRoute(role, s.slug));
    return { group, extraSlugs, modules, services };
  }).filter((g) => g.extraSlugs.length > 0 || g.modules.length > 0 || g.services.length > 0);
}
