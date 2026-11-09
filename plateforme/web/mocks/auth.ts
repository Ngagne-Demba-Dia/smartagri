/**
 * Comptes de démonstration (un par rôle) et jetons simulés. Mot de passe unique « demo » : ces comptes
 * n'existent que dans la simulation (AGRI_MOCK=1) ; l'interface nomme des rôles, jamais des personnes.
 */
import type { Me, Role } from "@/lib/types";

import { ORG_A, ORG_A_NAME, ORG_B, ORG_B_NAME } from "./fixtures/places";

export const DEMO_PASSWORD = "demo";
export const TOKEN_TTL_S = 3600;
const ACCESS_PREFIX = "mock-access-";
const REFRESH_PREFIX = "mock-refresh-";

const coop = (role: Role) => ({
  organization_id: ORG_A,
  organization_name: ORG_A_NAME,
  organization_kind: "cooperative" as const,
  role,
});
const farm = (role: Role) => ({
  organization_id: ORG_B,
  organization_name: ORG_B_NAME,
  organization_kind: "farm" as const,
  role,
});

interface DemoAccount {
  username: string;
  me: Me;
}

const account = (role: Role, username: string, memberships: Me["memberships"]): DemoAccount => ({
  username,
  me: { id: `usr-demo-${role}`, full_name: null, email: username, phone: null, locale: "fr", memberships },
});

/** L'administrateur voit les deux organisations ; les autres comptes, une seule. */
export const DEMO_ACCOUNTS: Readonly<Record<Role, DemoAccount>> = {
  farmer: account("farmer", "agriculteur@demo.sn", [farm("farmer")]),
  coop_manager: account("coop_manager", "cooperative@demo.sn", [coop("coop_manager")]),
  agronomist: account("agronomist", "agronome@demo.sn", [coop("agronomist")]),
  admin: account("admin", "admin@demo.sn", [coop("admin"), farm("admin")]),
};

const ROLES = Object.keys(DEMO_ACCOUNTS) as Role[];

export interface Principal {
  role: Role;
  me: Me;
  /** Organisations visibles : un objet d'une autre organisation répond 404 (CONVENTIONS §5). */
  orgIds: ReadonlySet<string>;
}

function principal(role: Role): Principal {
  const { me } = DEMO_ACCOUNTS[role];
  return { role, me, orgIds: new Set(me.memberships.map((m) => m.organization_id)) };
}

export function roleForCredentials(username: string, password: string): Role | null {
  if (password !== DEMO_PASSWORD) return null;
  const wanted = username.trim().toLowerCase();
  return ROLES.find((role) => DEMO_ACCOUNTS[role].username === wanted) ?? null;
}

export function tokenPair(role: Role) {
  return {
    access_token: `${ACCESS_PREFIX}${role}`,
    refresh_token: `${REFRESH_PREFIX}${role}`,
    token_type: "bearer",
    expires_in: TOKEN_TTL_S,
  };
}

function roleFromToken(token: string, prefix: string): Role | null {
  if (!token.startsWith(prefix)) return null;
  const role = token.slice(prefix.length);
  return (ROLES as string[]).includes(role) ? (role as Role) : null;
}

export function roleFromRefreshToken(token: unknown): Role | null {
  return typeof token === "string" ? roleFromToken(token, REFRESH_PREFIX) : null;
}

/** Authorization: Bearer mock-access-<rôle> ; null → 401 UNAUTHENTICATED. */
export function principalFromRequest(request: Request): Principal | null {
  const header = request.headers.get("authorization") ?? "";
  const match = /^Bearer\s+(\S+)$/i.exec(header);
  const token = match?.[1];
  const role = token ? roleFromToken(token, ACCESS_PREFIX) : null;
  return role ? principal(role) : null;
}
