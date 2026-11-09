/**
 * Socle des 18 services d'IA (doc 16 §9) : appel du BFF same-origin puis validation par le contrat.
 * Les composants ne voient que ces fonctions et les hooks : passer des simulations à l'API réelle
 * ne change que la cible du BFF (lib/server/upstream.ts), jamais un composant.
 */
import type { z } from "zod";

import type { ApiClient, QueryValue } from "@/lib/api";
import { api } from "@/lib/client";
import { parseContract } from "@/lib/contracts/envelope";
import { serviceById, type ServiceId } from "@/lib/contracts/registry";

export interface CallOptions {
  client?: ApiClient;
  signal?: AbortSignal;
}

export async function getContract<S extends z.ZodType>(
  service: ServiceId,
  schema: S,
  path: string,
  query?: Record<string, QueryValue>,
  options: CallOptions = {},
): Promise<z.output<S>> {
  const client = options.client ?? api;
  const { data } = await client.get<unknown>(path, query, options.signal);
  return parseContract(schema, data, service);
}

export async function postContract<S extends z.ZodType>(
  service: ServiceId,
  schema: S,
  path: string,
  body: unknown,
  options: CallOptions = {},
): Promise<z.output<S>> {
  const client = options.client ?? api;
  const { data } = await client.post<unknown>(path, body);
  return parseContract(schema, data, service);
}

/** Durée de fraîcheur côté front d'un service (doc 16 §9.4). */
export const staleFor = (service: ServiceId): number => serviceById(service).staleMs;

/** Segment d'URL sûr ; les identifiants viennent de l'API ou de l'URL. */
export const seg = (id: string): string => encodeURIComponent(id);
