/**
 * Droits d'affichage côté interface, alignés sur backend/app/core/constants.py.
 * Ils ne servent qu'à masquer les actions impossibles : l'API reste seule juge (403 sinon).
 */
import type { Me, Role } from "./types";

export const THRESHOLD_WRITERS: ReadonlySet<Role> = new Set<Role>(["farmer", "coop_manager", "admin"]);
export const FEEDBACK_WRITERS: ReadonlySet<Role> = new Set<Role>(["farmer", "coop_manager", "admin"]);
export const ALERT_ACKERS: ReadonlySet<Role> = new Set<Role>(["farmer", "coop_manager", "agronomist", "admin"]);

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
