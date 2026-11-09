/**
 * Périmètre de l'utilisateur simulé (CONVENTIONS §5) : un objet d'une autre organisation, ou inconnu,
 * répond 404 NOT_FOUND ; un rôle insuffisant répond 403 FORBIDDEN (règles de lib/roles.ts).
 */
import type { Farm } from "@/lib/types";

import type { Principal } from "./auth";
import {
  DEVICE_SEEDS,
  FARMS,
  FIELD_SEEDS,
  deviceSeedById,
  farmById,
  fieldSeedById,
  type DeviceSeed,
  type FieldSeed,
} from "./fixtures/places";

const sees = (user: Principal, orgId: string): boolean => user.orgIds.has(orgId);

export function visibleFarm(user: Principal, farmId: string): Farm | null {
  const farm = farmById(farmId);
  return farm && sees(user, farm.organization_id) ? farm : null;
}

export function visibleField(user: Principal, fieldId: string): FieldSeed | null {
  const seed = fieldSeedById(fieldId);
  return seed && sees(user, seed.orgId) ? seed : null;
}

export function visibleDevice(user: Principal, deviceId: string): DeviceSeed | null {
  const seed = deviceSeedById(deviceId);
  return seed && sees(user, seed.orgId) ? seed : null;
}

export const visibleFarms = (user: Principal): Farm[] => FARMS.filter((f) => sees(user, f.organization_id));
export const visibleFieldSeeds = (user: Principal): FieldSeed[] => FIELD_SEEDS.filter((f) => sees(user, f.orgId));
export const visibleDeviceSeeds = (user: Principal): DeviceSeed[] => DEVICE_SEEDS.filter((d) => sees(user, d.orgId));
