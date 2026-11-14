"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Meter } from "@/components/Meter";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { useCampaigns } from "@/hooks/reports";
import { campaignProgress, daysLeft, sortedCampaigns } from "@/lib/campaigns";
import { formatDate } from "@/lib/format";
import type { Tone } from "@/lib/status";
import type { Campaign, CampaignStatus } from "@/lib/types";

const STATUS_TONE: Record<CampaignStatus, Tone> = { planned: "info", active: "ok", closed: "info" };

function Progress({ campaign, now }: { campaign: Campaign; now: Date }) {
  const t = useTranslations("campaigns");
  if (campaign.status === "planned") {
    return <p className="text-sm text-mute">{t("startsOn", { date: formatDate(campaign.start_date) })}</p>;
  }
  const pct = campaignProgress(campaign, now);
  if (pct === null) return <p className="text-sm text-mute">{t("datesUnknown")}</p>;
  const left = daysLeft(campaign, now);
  return (
    <div className="flex flex-col gap-1">
      <Meter
        value={pct}
        label={t("progressLabel", { name: campaign.name })}
        valueText={t("progressValue", { pct })}
      />
      <p className="text-sm text-mute">
        {campaign.status === "closed"
          ? t("closedOn", { date: formatDate(campaign.end_date) })
          : left !== null
            ? t("daysLeft", { count: left })
            : t("progressValue", { pct })}
      </p>
    </div>
  );
}

function CampaignCard({ campaign, now }: { campaign: Campaign; now: Date }) {
  const t = useTranslations("campaigns");
  const seasonLabel = t.has(`seasons.${campaign.season}`) ? t(`seasons.${campaign.season}`) : campaign.season;
  return (
    <li className="card flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="break-words text-lg font-semibold">{campaign.name}</h2>
        <StatusTag tone={STATUS_TONE[campaign.status]} label={t(`status.${campaign.status}`)} />
      </div>
      <p className="text-sm text-mute">
        {t("season", { season: seasonLabel })} ·{" "}
        {t("period", { start: formatDate(campaign.start_date), end: formatDate(campaign.end_date) })}
      </p>
      <Progress campaign={campaign} now={now} />
    </li>
  );
}

/** Campagnes (module 11) : saisons de l'organisation et part de la période écoulée (lecture seule). */
export function CampaignsView() {
  const t = useTranslations("campaigns");
  const tm = useTranslations("modules");
  const campaigns = useCampaigns();
  const [now] = useState(() => new Date());
  const rows = campaigns.data ?? [];

  return (
    <ModuleShell title={tm("campaigns")} description={t("description")} version="V1_1">
      <QueryState
        isPending={campaigns.isPending}
        error={campaigns.error}
        isEmpty={rows.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => void campaigns.refetch()}
      >
        <ul aria-label={t("listLabel")} className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {sortedCampaigns(rows).map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} now={now} />
          ))}
        </ul>
      </QueryState>
    </ModuleShell>
  );
}
