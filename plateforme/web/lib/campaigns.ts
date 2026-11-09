/** Campagnes (module 11) : tri et avancement calculés côté client, sans rien inventer. */
import type { Campaign, CampaignStatus } from "./types";

const DAY_MS = 86_400_000;
const STATUS_ORDER: Record<CampaignStatus, number> = { active: 0, planned: 1, closed: 2 };

/** En cours d'abord, puis prévues, puis closes ; à statut égal, la plus récente en premier. */
export function sortedCampaigns(campaigns: readonly Campaign[]): Campaign[] {
  return [...campaigns].sort(
    (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || b.start_date.localeCompare(a.start_date),
  );
}

/**
 * Part écoulée de la campagne, en % (0–100). Une campagne prévue vaut 0, une campagne close 100 ;
 * une campagne en cours est située par les dates. Null si les dates sont illisibles ou inversées.
 */
export function campaignProgress(campaign: Campaign, now: Date): number | null {
  if (campaign.status === "planned") return 0;
  if (campaign.status === "closed") return 100;
  const start = Date.parse(campaign.start_date);
  const end = Date.parse(campaign.end_date);
  if (Number.isNaN(start) || Number.isNaN(end) || end <= start) return null;
  const share = ((now.getTime() - start) / (end - start)) * 100;
  return Math.round(Math.min(100, Math.max(0, share)));
}

/** Jours restant avant la fin ; null hors campagne en cours ou si la date est illisible. */
export function daysLeft(campaign: Campaign, now: Date): number | null {
  if (campaign.status !== "active") return null;
  const end = Date.parse(campaign.end_date);
  if (Number.isNaN(end)) return null;
  return Math.max(0, Math.ceil((end - now.getTime()) / DAY_MS));
}
