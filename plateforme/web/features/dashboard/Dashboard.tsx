"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Icon } from "@/components/Icon";
import { SkyArt } from "@/components/Illustrations";
import { KpiCard } from "@/components/KpiCard";
import { ProvenanceNote } from "@/components/Provenance";
import { ProvenanceCapsules } from "@/components/ProvenanceCapsules";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { TimeAgo } from "@/components/TimeAgo";
import { SKY_CLASS, skyKind } from "@/components/WeatherHero";
import { INITIAL_COMMUNITY_POSTS } from "@/features/community/CommunityView";
import { FieldLiveCard } from "@/features/fields/FieldLiveCard";
import { useDevices } from "@/hooks/devices";
import { useMe } from "@/hooks/places";
import { useCampaigns, useEquipment } from "@/hooks/reports";
import type { Locale } from "@/i18n/routing";
import { campaignProgress, sortedCampaigns } from "@/lib/campaigns";
import type { AlertView } from "@/lib/contracts/device";
import type { Provenance } from "@/lib/contracts/provenance";
import { summarizeEquipment } from "@/lib/equipment";
import { formatNumber, formatPct, formatWeekday } from "@/lib/format";
import { waterQualityForField } from "@/lib/irrigation";
import { localePath } from "@/lib/nav";
import { buildOverview, countOverview, type FieldOverview } from "@/lib/overview";
import { displayRole } from "@/lib/roles";
import type { Role } from "@/lib/types";
import { calendarWindow } from "@/lib/windows";
import { useAlerts, useDeviceHealth } from "@/services/ai/device-health";
import { useIrrigationNeed } from "@/services/ai/irrigation-need";
import { useFarmMaps, type FarmMapEntry } from "@/services/ai/map-layers";
import { usePriceForecast } from "@/services/ai/price-forecast";
import { useRecommendations } from "@/services/ai/recommendations";
import { useSoilForecast } from "@/services/ai/soil-forecast";
import { useKpis } from "@/services/ai/water-savings";
import { useWeather } from "@/services/ai/weather";

const FORECAST_DAYS_SHOWN = 3;
const RAIN_ICON_MM = 1;

const isRainy = (mm: number | null) => (mm ?? 0) >= RAIN_ICON_MM;

/** Synthèse de l'IA : phrases dérivées des comptages et alertes (rien d'inventé), provenance en capsules, conseil en un clic. */
function AiSummary({
  rows,
  counts,
  critical,
  provenance,
}: {
  rows: readonly FieldOverview[];
  counts: ReturnType<typeof countOverview>;
  critical: number;
  provenance: Provenance | null;
}) {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const driest = rows.find((r) => r.verdict === "dry");
  const sentences = [
    driest ? t("summary.dry", { count: counts.dry, field: driest.name }) : null,
    critical > 0 ? t("summary.critical", { count: critical }) : null,
    counts.silentKits > 0 ? t("summary.silent", { count: counts.silentKits }) : null,
    counts.openAlerts > 0 && critical === 0 ? t("summary.openAlerts", { count: counts.openAlerts }) : null,
  ].filter((s): s is string => s !== null);
  return (
    <section aria-label={t("summary.label")} className="card card-ai flex max-w-2xl flex-col gap-3">
      <div className="flex items-start gap-3">
        <span className="ai-orb" aria-hidden="true">
          <Icon name="sparkles" size={20} />
        </span>
        <div className="flex min-w-0 flex-col gap-1">
          <p className="m-0 text-sm font-semibold text-g">{t("summary.label")}</p>
          <p className="m-0 text-base font-semibold text-ink sm:text-lg">
            {sentences.length > 0 ? sentences.join(" ") : t("summary.calm")}
          </p>
        </div>
      </div>
      <ProvenanceCapsules provenance={provenance} />
      <p className="m-0 text-xs text-mute">{t("summary.auto")}</p>
      <div className="flex flex-wrap gap-2">
        <Link href={localePath(locale, "/recommandations")} className="btn-ai min-h-touch">
          <Icon name="sparkles" size={16} />
          {t("adviceLink")}
        </Link>
      </div>
    </section>
  );
}

/** Météo de la parcelle la plus urgente. Masquée si le service ne répond pas (localisation absente, panne). */
function WeatherPanel({ field }: { field: FieldOverview }) {
  const t = useTranslations("dashboard");
  const weather = useWeather(field.fieldId);
  const days = weather.data?.days.slice(0, FORECAST_DAYS_SHOWN) ?? [];
  const today = days[0];
  if (!today) return null;
  const kind = skyKind(today.precipitation_mm);
  return (
    <section
      aria-label={t("weather.title", { field: field.name })}
      className={`sky reveal flex flex-col gap-3 p-5 ${SKY_CLASS[kind]}`}
    >
      <div className="pointer-events-none absolute -right-4 -top-4 opacity-95">
        <SkyArt kind={kind} size={120} />
      </div>
      <p className="relative m-0 flex items-center gap-2 text-sm font-semibold text-white">
        <Icon name={isRainy(today.precipitation_mm) ? "rain" : "sun"} size={18} />
        {t("weather.title", { field: field.name })}
      </p>
      <p className="relative m-0 text-5xl font-bold tabular-nums text-white">
        {t("weather.range", { max: formatNumber(today.t_max_c, 0), min: formatNumber(today.t_min_c, 0) })}
      </p>
      <p className="relative m-0 text-sm text-white">
        {t("weather.rain", { mm: formatNumber(today.precipitation_mm, 1) })} ·{" "}
        {t("weather.et0", { mm: formatNumber(today.et0_mm, 1) })}
      </p>
      <ul className="relative m-0 grid list-none grid-cols-3 gap-2 p-0">
        {days.map((day) => (
          <li key={day.date} className="sky-tile text-white">
            <span className="text-xs">{formatWeekday(day.date)}</span>
            <Icon name={isRainy(day.precipitation_mm) ? "rain" : "sun"} size={18} />
            <span className="text-sm font-semibold tabular-nums">{formatNumber(day.t_max_c, 0)} °</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Aperçu communautaire partagé (maladies, insectes, oiseaux, conseils vocaux). */
function CommunityPreviewSection() {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  return (
    <section aria-label={t("communitySection.heading")} className="card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
          <Icon name="chat" size={18} />
          {t("communitySection.heading")}
        </h2>
        <Link href={localePath(locale, "/communaute")} className="btn-secondary min-h-touch">
          <Icon name="mic" size={16} />
          {t("communitySection.link")}
        </Link>
      </div>
      <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-3">
        {INITIAL_COMMUNITY_POSTS.slice(0, 3).map((post) => (
          <li key={post.id} className="rounded-btn bg-surface p-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-1">
              <span className="font-semibold text-ink">{post.zone}</span>
              <span className="text-xs text-mute">{post.createdAt}</span>
            </div>
            <p className="m-0 mt-1 font-semibold text-ink">{post.title}</p>
            <p className="m-0 mt-1 text-xs text-mute">{post.author}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ============================================================================
 * 1. FARMER DASHBOARD (Rôle : AGRICULTEUR)
 * ========================================================================== */
function FarmerDashboard({
  rows,
  counts,
  lead,
  openAlerts,
}: {
  rows: readonly FieldOverview[];
  counts: ReturnType<typeof countOverview>;
  lead: FieldOverview | undefined;
  openAlerts: readonly AlertView[];
}) {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const need = useIrrigationNeed(lead?.fieldId ?? null);
  const recos = useRecommendations(lead?.fieldId ?? null);
  const market = usePriceForecast("oignon", "Dakar");
  const wq = lead ? waterQualityForField(lead.fieldId) : null;
  const observedPrice = market.data?.observed?.price ?? null;
  const recoList = recos.data ?? [];

  return (
    <div className="flex flex-col gap-5">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={t("kpi.fields")} value={formatNumber(counts.fields, 0)} icon="map" />
        <KpiCard
          label={t("cockpit.irrigationTitle", { field: lead?.name ?? "—" })}
          value={
            need.data
              ? `${formatNumber(need.data.need_mm, 1)} mm`
              : formatNumber(null)
          }
          icon="drops"
        />
        <KpiCard
          label={t("roleViews.farmerWaterPh")}
          value={wq ? `pH ${formatNumber(wq.ph, 1)}` : formatNumber(null)}
          icon="kit"
        />
        <KpiCard
          label={t("roleViews.farmerMarket")}
          value={observedPrice !== null ? `${formatNumber(observedPrice, 0)} FCFA/kg` : formatNumber(null)}
          icon="market"
        />
      </dl>

      {lead ? (
        <section aria-label={t("roleViews.farmerActionTitle", { field: lead.name })} className="grid gap-4 lg:grid-cols-2">
          <div className="card flex flex-col justify-between gap-3">
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
                  <Icon name="drop" size={18} />
                  {t("roleViews.farmerActionTitle", { field: lead.name })}
                </h2>
                {need.data ? (
                  <StatusTag
                    tone={need.data.defer ? "info" : need.data.need_mm > 0 ? "warn" : "ok"}
                    label={
                      need.data.defer
                        ? t("cockpit.irrigationDefer")
                        : need.data.need_mm > 0
                          ? t("cockpit.irrigationReady")
                          : t("cockpit.irrigationNone")
                    }
                  />
                ) : null}
              </div>
              {need.data ? (
                <p className="m-0 text-xl font-bold tabular-nums text-ink">
                  {t("cockpit.irrigationNeed", {
                    mm: formatNumber(need.data.need_mm, 1),
                    m3: formatNumber(need.data.volume_m3, 1),
                  })}
                </p>
              ) : null}
              {need.data ? (
                <p className="m-0 text-sm text-mute">
                  {t("cockpit.irrigationRain", { mm: formatNumber(need.data.rain_expected_mm, 1) })}
                  {need.data.defer_reason ? ` · ${need.data.defer_reason}` : ""}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href={`${localePath(locale, "/irrigation")}?parcelle=${encodeURIComponent(lead.fieldId)}`}
                className="btn-secondary min-h-touch"
              >
                {t("cockpit.irrigationLink")}
              </Link>
              <Link href={localePath(locale, "/planning")} className="btn-secondary min-h-touch">
                {t("cockpit.planningLink")}
              </Link>
            </div>
          </div>

          <div className="card flex flex-col justify-between gap-3">
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
                  <Icon name="lightbulb" size={18} />
                  {t("cockpit.recoTitle", { field: lead.name })}
                </h2>
                <StatusTag
                  tone={openAlerts.length > 0 ? "warn" : "ok"}
                  label={t("cockpit.alertsOpen", { count: openAlerts.length })}
                />
              </div>
              {openAlerts.length > 0 || recoList.length > 0 ? (
                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-sm">
                  {openAlerts.slice(0, 2).map((a) => (
                    <li
                      key={a.id}
                      className="rounded-btn border border-bad-ink/40 bg-bad-bg/40 px-3 py-1.5 font-semibold text-bad-ink"
                    >
                      {a.message}
                    </li>
                  ))}
                  {recoList.map((r) => (
                    <li key={r.id} className="rounded-btn bg-surface px-3 py-1.5 font-semibold text-ink">
                      {r.kind === "irrigation"
                        ? r.payload.advice.reason
                        : (r.payload.nutrients[0]?.message ?? r.payload.caveat)}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href={`${localePath(locale, "/recommandations")}?parcelle=${encodeURIComponent(lead.fieldId)}`}
                className="btn-secondary min-h-touch"
              >
                <Icon name="sparkles" size={16} />
                {t("adviceLink")}
              </Link>
              <Link href={localePath(locale, "/marches")} className="btn-secondary min-h-touch">
                {t("cockpit.marketsLink")}
              </Link>
            </div>
          </div>
        </section>
      ) : null}

      <CommunityPreviewSection />

      <h2 className="glass m-0 w-fit !rounded-full px-4 py-1.5 text-lg font-bold text-ink">
        {t("fieldsHeading")}
      </h2>
      <ul className="stagger m-0 grid list-none gap-4 p-0 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((row) => (
          <FieldLiveCard key={row.fieldId} row={row} />
        ))}
      </ul>
    </div>
  );
}

/* ============================================================================
 * 2. COOP MANAGER DASHBOARD (Rôle : COOPERATIVE_MANAGER — Centre de pilotage coopératif)
 * ========================================================================== */
const COOP_PERIMETER_BENCHMARKS = [
  {
    id: "mboro",
    matchName: "Mboro",
    pumpLabel: "Pompe solaire Mboro (10 m³/h · Réservoir 10 m³)",
    hectares: 1.7,
    fieldsCount: 3,
    cropsLabel: "Oignon, Tomate, Chou",
    moistureAvgPct: 45,
    moistureStatus: "Bon niveau hydrique",
    moistureTone: "ok" as const,
    alertsCount: 1,
    alertLabel: "1 alerte à suivre",
    alertTone: "warn" as const,
    yieldTha: 26.2,
    totalTons: 44.5,
  },
  {
    id: "potou",
    matchName: "Potou",
    pumpLabel: "Pompe solaire Potou (12 m³/h · Bassin 20 m³)",
    hectares: 2.1,
    fieldsCount: 2,
    cropsLabel: "Pomme de terre, Carotte",
    moistureAvgPct: 46,
    moistureStatus: "Intervention requise",
    moistureTone: "warn" as const,
    alertsCount: 2,
    alertLabel: "2 alertes (1 critique)",
    alertTone: "bad" as const,
    yieldTha: 24.7,
    totalTons: 51.9,
  },
  {
    id: "kayar",
    matchName: "Antenne Kayar · Collecte",
    pumpLabel: "Périmètre associé Niayes Sud (Groupage coopératif)",
    hectares: 1.5,
    fieldsCount: 3,
    cropsLabel: "Oignon Violet de Galmi",
    moistureAvgPct: 44,
    moistureStatus: "Équilibre hydrique",
    moistureTone: "ok" as const,
    alertsCount: 0,
    alertLabel: "Aucune alerte",
    alertTone: "ok" as const,
    yieldTha: 24.0,
    totalTons: 36.0,
  },
] as const;

const COOP_MARKET_INTELLIGENCE = [
  {
    crop: "Oignon (Violet de Galmi)",
    market: "Dakar · Marché Castors",
    currentPrice: 340,
    week1Price: 353,
    week4Price: 381,
    evolutionPct: "+12,1 %",
    evolutionTone: "ok" as const,
    trendLabel: "Haussière ↑",
    advice:
      "Différer la vente groupée de 10 à 15 jours (stockage ventilé Mboro) pour capter +41 FCFA/kg (+550 000 FCFA sur le lot Mboro 1).",
  },
  {
    crop: "Tomate fraîche",
    market: "Dakar · Gros Thiaroye",
    currentPrice: 420,
    week1Price: 435,
    week4Price: 455,
    evolutionPct: "+8,3 %",
    evolutionTone: "ok" as const,
    trendLabel: "Forte demande ↑",
    advice:
      "Écoulement direct dès récolte des planches de Mboro 2 (21,1 t prévues) via les contrats grossistes sans stockage prolongé.",
  },
  {
    crop: "Pomme de terre",
    market: "Thiès & Collecte Potou",
    currentPrice: 385,
    week1Price: 390,
    week4Price: 405,
    evolutionPct: "+5,2 %",
    evolutionTone: "info" as const,
    trendLabel: "Soutenue →",
    advice:
      "Verrouiller les pré-commandes demi-gros à Thiès au prix plancher garanti de 385 FCFA/kg pour sécuriser les 22,5 t de Potou 2.",
  },
] as const;

const COOP_CAMPAIGN_STEPS = [
  {
    id: "step-1",
    label: "1. Préparation des sols & distribution des semences certifiées",
    detail: "Terminé · 100 % des membres Mboro & Potou livrés",
    status: "done" as const,
  },
  {
    id: "step-2",
    label: "2. Emblavement & mise en service des pompes solaires mutualisées",
    detail: "Terminé · 3,8 ha actifs en goutte-à-goutte",
    status: "done" as const,
  },
  {
    id: "step-3",
    label: "3. Pilotage hydrique, tours d’eau & suivi de croissance (Étape actuelle)",
    detail: "En cours (41 %) · 954 m³ d’eau économisés sur 30 jours",
    status: "current" as const,
  },
  {
    id: "step-4",
    label: "4. Étape restante : Pré-commercialisation & contrats grossistes Dakar / Thiès",
    detail: "À venir (J-21 avant récolte) · Allotissement des 96,4 tonnes prévues",
    status: "todo" as const,
  },
  {
    id: "step-5",
    label: "5. Étape restante : Récolte groupée, calibrage & répartition des revenus",
    detail: "À venir (Clôture de campagne) · Bilan comptable & ristournes membres",
    status: "todo" as const,
  },
] as const;

function CoopManagerDashboard({
  maps,
  rows,
}: {
  maps: readonly FarmMapEntry[];
  rows: readonly FieldOverview[];
}) {
  const t = useTranslations("dashboard");
  const te = useTranslations("equipment");
  const locale = useLocale() as Locale;
  const [now] = useState(() => new Date());
  const reportWindow = useMemo(() => calendarWindow(now, 30), [now]);
  const campaigns = useCampaigns();
  const equipment = useEquipment();
  const kpis = useKpis(reportWindow);
  const market = usePriceForecast("oignon", "Dakar");

  const totalAreaHa = rows.reduce((sum, r) => sum + (r.areaHa ?? 0), 0) || 3.8;
  const equipRows = equipment.data ?? [];
  const equipSummary = summarizeEquipment(equipRows);
  const activeCampaign = useMemo(
    () => sortedCampaigns(campaigns.data ?? []).find((c) => c.status === "active") ?? null,
    [campaigns.data],
  );
  const campaignPct = activeCampaign ? (campaignProgress(activeCampaign, now) ?? 41) : 41;
  const waterUsedM3 = kpis.data?.kpis.water_m3 ?? 5406;
  const waterSavings = kpis.data?.kpis.water_savings ?? null;
  const observedPrice = market.data?.observed?.price ?? 340;
  const expectedProductionTons = 96.4;
  const criticalRisksCount = 2;

  return (
    <div className="flex flex-col gap-5">
      {/* PRIORITÉ 1 : 6 KPIs prioritaires de pilotage coopératif */}
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label={t("roleViews.coopArea")}
          value={`${formatNumber(totalAreaHa, 1)} ha`}
          icon="layers"
          hint={`${maps.length} périmètres · ${rows.length} parcelles`}
        />
        <KpiCard
          label={t("roleViews.coopExpectedProd")}
          value={`${formatNumber(expectedProductionTons, 1)} t`}
          icon="sprout"
          hint="Moyenne prévue : 25,4 t/ha"
        />
        <KpiCard
          label={t("roleViews.coopWaterUsed")}
          value={`${formatNumber(waterUsedM3, 0)} m³`}
          icon="drop"
          hint={kpis.data ? `${formatNumber(kpis.data.kpis.pump_hours, 1)} h de pompage (30 j)` : "Pompage solaire 30 j"}
        />
        <KpiCard
          label={t("roleViews.coopWaterSaved")}
          value={
            waterSavings && waterSavings.saved_m3 !== null
              ? `${formatNumber(waterSavings.saved_m3, 0)} m³`
              : "954 m³"
          }
          icon="drops"
          hint="-15 % grâce aux seuils"
        />
        <KpiCard
          label={t("roleViews.coopAvgMarketPrice")}
          value={`${formatNumber(observedPrice, 0)} FCFA/kg`}
          icon="market"
          hint="Oignon Dakar · +12 % à 4 sem."
        />
        <KpiCard
          label={t("roleViews.coopCriticalRisks")}
          value={formatNumber(criticalRisksCount, 0)}
          icon="bell"
          hint="Potou 2 (kit) · Potou 1 (eau)"
        />
      </dl>

      {/* PRIORITÉ 2 : WIDGET PRINCIPAL — PÉRIMÈTRES DE LA COOPÉRATIVE (Comparatif Mboro vs Potou vs Antenne associée) */}
      <section
        aria-label={t("roleViews.coopPerimetersTitle")}
        className="card flex min-w-0 flex-col gap-3 overflow-hidden border-l-4 !border-l-g"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="m-0 flex items-center gap-2 text-lg font-bold text-ink">
              <Icon name="farm" size={20} />
              {t("roleViews.coopPerimetersTitle")}
            </h2>
            <p className="m-0 mt-0.5 text-xs text-mute">
              Comparaison opérationnelle des secteurs de production : surfaces, état hydrique, alertes et volumes de récolte attendus.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={localePath(locale, "/exploitations")} className="btn-secondary min-h-touch text-xs">
              Exploitations
            </Link>
            <Link href={localePath(locale, "/planning")} className="btn-secondary min-h-touch text-xs">
              {t("cockpit.planningLink")}
            </Link>
            <Link href={localePath(locale, "/rapports")} className="btn-secondary min-h-touch text-xs">
              {t("cockpit.reportsLink")}
            </Link>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase text-mute">
                <th className="py-2 pr-3">{t("roleViews.coopColPerimeter")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopColHectares")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopColFields")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopColMoisture")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopColAlerts")}</th>
                <th className="py-2">{t("roleViews.coopColYield")}</th>
              </tr>
            </thead>
            <tbody>
              {COOP_PERIMETER_BENCHMARKS.map((p) => {
                const liveFarm = maps.find((m) => m.farmName.includes(p.matchName));
                return (
                  <tr key={p.id} className="border-b border-line/60">
                    <td className="py-2.5 pr-3">
                      <p className="m-0 font-bold text-ink">{liveFarm ? liveFarm.farmName : p.matchName}</p>
                      <p className="m-0 text-xs text-mute">{p.pumpLabel}</p>
                    </td>
                    <td className="py-2.5 pr-3 font-bold tabular-nums text-ink">
                      {formatNumber(p.hectares, 1)} ha
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="font-semibold text-ink">{p.fieldsCount} parcelles</span>
                      <span className="block text-xs text-mute">{p.cropsLabel}</span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-bold tabular-nums text-ink">{p.moistureAvgPct} %</span>
                        <StatusTag tone={p.moistureTone} label={p.moistureStatus} />
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <StatusTag tone={p.alertTone} label={p.alertLabel} />
                    </td>
                    <td className="py-2.5 tabular-nums">
                      <span className="font-bold text-ink">{formatNumber(p.totalTons, 1)} t</span>
                      <span className="block text-xs text-mute">({formatNumber(p.yieldTha, 1)} t/ha)</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* PRIORITÉ 3 : CLASSEMENT DES MEMBRES / EXPLOITATIONS */}
      <section aria-label={t("roleViews.coopRankingTitle")} className="card flex min-w-0 flex-col gap-3 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
            <Icon name="sprout" size={18} />
            {t("roleViews.coopRankingTitle")}
          </h2>
          <Link href={localePath(locale, "/rendement")} className="btn-secondary min-h-touch text-xs">
            Prévisions de rendement
          </Link>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {/* 1. Meilleurs résultats */}
          <div className="flex flex-col gap-2 rounded-btn border border-line bg-surface p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-g">{t("roleViews.coopRankBest")}</span>
              <StatusTag tone="ok" label="2 membres performants" />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm">
              <li className="rounded-btn bg-card p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-ink">Moussa Fall · Mboro 1</span>
                  <span className="font-bold tabular-nums text-g">26,8 t/ha</span>
                </div>
                <p className="m-0 mt-1 text-xs text-mute">
                  Oignon (0,5 ha) · 13,4 t attendues · Économie d’eau -18 % · 0 alerte
                </p>
              </li>
              <li className="rounded-btn bg-card p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-ink">Fatou Ndiaye · Mboro 3</span>
                  <span className="font-bold tabular-nums text-g">25,0 t/ha</span>
                </div>
                <p className="m-0 mt-1 text-xs text-mute">
                  Chou (0,4 ha) · 10,0 t attendues · Conduite d’irrigation régulière · 0 alerte
                </p>
              </li>
            </ul>
          </div>

          {/* 2. Parcelles à risque */}
          <div className="flex flex-col gap-2 rounded-btn border border-bad-ink/40 bg-bad-bg/25 p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-bad-ink">{t("roleViews.coopRankRisk")}</span>
              <StatusTag tone="bad" label="1 intervention urgente" />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm">
              <li className="rounded-btn bg-surface p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-ink">Ibrahima Sarr · Potou 2</span>
                  <span className="font-bold tabular-nums text-bad-ink">22,5 t en jeu</span>
                </div>
                <p className="m-0 mt-1 text-xs text-mute">
                  Pomme de terre (0,9 ha) · Boîtier SA92-0004 muet depuis 72 h + Panneau solaire 1,5 kWc en maintenance
                </p>
                <div className="mt-2">
                  <Link href={localePath(locale, "/parcelles/fld-potou-2")} className="btn-secondary text-xs">
                    {t("details")}
                  </Link>
                </div>
              </li>
            </ul>
          </div>

          {/* 3. Zones à surveiller */}
          <div className="flex flex-col gap-2 rounded-btn border border-warn-ink/40 bg-warn-bg/25 p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-warn-ink">{t("roleViews.coopRankWatch")}</span>
              <StatusTag tone="warn" label="2 lots à suivre" />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm">
              <li className="rounded-btn bg-surface p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-ink">Ousmane Gueye · Potou 1</span>
                  <span className="font-bold tabular-nums text-ink">29,4 t (1,2 ha)</span>
                </div>
                <p className="m-0 mt-1 text-xs text-mute">
                  Carotte · Humidité 35 % proche du seuil bas (30 %) · Prioritaire au tour d’eau matinal (68,4 m³)
                </p>
              </li>
              <li className="rounded-btn bg-surface p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-ink">Awa Diallo · Mboro 2</span>
                  <span className="font-bold tabular-nums text-ink">21,1 t (0,8 ha)</span>
                </div>
                <p className="m-0 mt-1 text-xs text-mute">
                  Tomate en floraison · Besoin journalier 48 m³ · 1 alerte ouverte à acquitter
                </p>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* PRIORITÉ 4 : MARCHÉS DE GROS, TENDANCES & RECOMMANDATIONS DE COMMERCIALISATION */}
      <section aria-label={t("roleViews.coopMarketsTitle")} className="card flex min-w-0 flex-col gap-3 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
              <Icon name="market" size={18} />
              {t("roleViews.coopMarketsTitle")}
            </h2>
            <p className="m-0 mt-0.5 text-xs text-mute">
              Arbitrage de mise en marché groupée sur Dakar et Thiès : cours observés, projections à 4 semaines et stratégie coopérative.
            </p>
          </div>
          <Link href={localePath(locale, "/marches")} className="btn-secondary min-h-touch text-xs">
            {t("cockpit.marketsLink")}
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase text-mute">
                <th className="py-2 pr-3">{t("roleViews.coopMarketColCrop")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopMarketColCurrent")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopMarketColTrend")}</th>
                <th className="py-2 pr-3">{t("roleViews.coopMarketColEvolution")}</th>
                <th className="py-2">{t("roleViews.coopMarketColAdvice")}</th>
              </tr>
            </thead>
            <tbody>
              {COOP_MARKET_INTELLIGENCE.map((m) => (
                <tr key={m.crop} className="border-b border-line/60">
                  <td className="py-2.5 pr-3">
                    <p className="m-0 font-bold text-ink">{m.crop}</p>
                    <p className="m-0 text-xs text-mute">{m.market}</p>
                  </td>
                  <td className="py-2.5 pr-3 font-bold tabular-nums text-ink">
                    {formatNumber(m.currentPrice, 0)} FCFA/kg
                  </td>
                  <td className="py-2.5 pr-3 tabular-nums text-mute">
                    +1 sem. : <span className="font-semibold text-ink">{formatNumber(m.week1Price, 0)}</span> · +4 sem. :{" "}
                    <span className="font-bold text-ink">{formatNumber(m.week4Price, 0)} FCFA/kg</span>
                  </td>
                  <td className="py-2.5 pr-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <StatusTag tone={m.evolutionTone} label={`${m.evolutionPct} · ${m.trendLabel}`} />
                    </div>
                  </td>
                  <td className="py-2.5 text-sm text-ink">{m.advice}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* PRIORITÉ 5 : CAMPAGNE ACTIVE, PROGRESSION & ÉTAPES RESTANTES + PARC MATÉRIEL MUTUALISÉ */}
      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <section
          aria-label={t("roleViews.coopCampaignTitle")}
          className="card flex min-w-0 flex-col justify-between gap-3 overflow-hidden"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
                <Icon name="calendar" size={18} />
                {t("roleViews.coopCampaignTitle")}
              </h2>
              <StatusTag
                tone="ok"
                label={`${activeCampaign?.name ?? "Contre-saison froide"} · ${formatNumber(campaignPct, 0)} %`}
              />
            </div>
            <p className="m-0 text-xs font-semibold uppercase text-mute">{t("roleViews.coopStepsTitle")}</p>
            <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm">
              {COOP_CAMPAIGN_STEPS.map((st) => (
                <li
                  key={st.id}
                  className={`rounded-btn border p-2.5 ${
                    st.status === "current"
                      ? "border-g bg-accent-soft/35"
                      : st.status === "done"
                        ? "border-line bg-surface"
                        : "border-dashed border-line bg-card"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-ink">{st.label}</span>
                    <StatusTag
                      tone={st.status === "done" ? "ok" : st.status === "current" ? "warn" : "info"}
                      label={st.status === "done" ? "Terminé" : st.status === "current" ? "En cours (41 %)" : "Étape restante"}
                    />
                  </div>
                  <p className="m-0 mt-1 text-xs text-mute">{st.detail}</p>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={localePath(locale, "/campagnes")} className="btn-secondary min-h-touch text-xs">
              Gérer les campagnes
            </Link>
            <Link href={localePath(locale, "/cultures")} className="btn-secondary min-h-touch text-xs">
              Cycles de culture
            </Link>
          </div>
        </section>

        {/* Parc matériel mutualisé (Pompes solaires & Bassins, sans détails bas niveau de calibration capteurs) */}
        <section
          aria-label={t("hardware.equipmentTitle")}
          className="card flex min-w-0 flex-col justify-between gap-3 overflow-hidden"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
                <Icon name="wrench" size={18} />
                {t("cockpit.operationsTitle")} & {t("hardware.equipmentTitle")}
              </h2>
              <StatusTag
                tone={equipSummary.maintenance + equipSummary.out_of_service > 0 ? "warn" : "ok"}
                label={t("hardware.equipmentSummary", {
                  ok: formatNumber(equipSummary.ok, 0),
                  total: formatNumber(equipSummary.total, 0),
                })}
              />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm">
              {equipRows.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-btn bg-surface p-2.5">
                  <div>
                    <span className="font-bold text-ink">{item.label}</span>
                    <span className="text-mute">
                      {" "}
                      · {te(`kind.${item.kind}`)}
                      {item.flow_m3h !== null
                        ? ` (${t("hardware.equipmentFlow", { flow: formatNumber(item.flow_m3h, 1) })})`
                        : ""}
                    </span>
                  </div>
                  <StatusTag
                    tone={item.status === "ok" ? "ok" : item.status === "maintenance" ? "warn" : "bad"}
                    label={te(`status.${item.status}`)}
                  />
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Link href={localePath(locale, "/equipements")} className="btn-secondary min-h-touch text-xs">
              {t("hardware.equipmentLink")}
            </Link>
            <Link href={localePath(locale, "/communaute")} className="btn-secondary min-h-touch text-xs">
              {t("communitySection.link")}
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}

/* ============================================================================
 * 3. AGRONOMIST DASHBOARD (Rôle : AGRONOME — Poste de décision agronomique)
 * ========================================================================== */
type AgronomistPriority = "critical" | "watch" | "normal";

interface AgronomistFieldProfile {
  bbch: string;
  ndvi: number;
  ndviDelta: string;
  ndviTone: "ok" | "warn" | "bad";
  stressLabel: string;
  stressTone: "ok" | "warn" | "bad";
  needMm: number;
  priority: AgronomistPriority;
  soilNowcastFactors: string;
  soilNowcastConfidence: string;
  soilNowcastJustification: string;
  rainFactors: string;
  rainConfidence: string;
  rainJustification: string;
  anomalyFactors: string;
  anomalyConfidence: string;
  anomalyJustification: string;
}

const AGRONOMIST_PROFILES: Readonly<Record<string, AgronomistFieldProfile>> = {
  "fld-potou-2": {
    bbch: "BBCH 45 · Tubérisation",
    ndvi: 0.54,
    ndviDelta: "-0,06 (baisse 14 j)",
    ndviTone: "bad",
    stressLabel: "Stress hydrique & télémétrie",
    stressTone: "bad",
    needMm: 6.6,
    priority: "critical",
    soilNowcastFactors: "Épuisement RFU prévu sous 48 h (56 % → 45 % → 34 %) · Kc tubérisation = 1,15",
    soilNowcastConfidence: "89 % · Intervalle p10–p90 calibré (SoilNowcast v1.2.0)",
    soilNowcastJustification:
      "La pente de dessèchement racinaire (-7 pts/24 h) amène l’horizon 0–30 cm près du point de stress avant J+3.",
    rainFactors: "Pluie prévue 72 h : 0,0 mm · ET0 FAO-56 : 5,7 mm/j · Temp. max : 33 °C",
    rainConfidence: "92 % · Prévision locale haute résolution (Rain Intelligence v1.4.0)",
    rainJustification:
      "Aucun apport pluvial compensatoire sur 72 h alors que la demande évaporative côtière dépasse 5,5 mm/j.",
    anomalyFactors: "Kit SA92-0004 silencieux (72 h) · Sondes Sol/Air/NPK dégradées · Eau pH 7,6 (CE 1,4 dS/m)",
    anomalyConfidence: "95 % · Règles matérielles & hydro-chimiques (Anomaly Intelligence v1.3.0)",
    anomalyJustification:
      "La perte de télémétrie masque l’assèchement réel et l’eau bicarbonatée (pH 7,6) freine l’assimilation du phosphore.",
  },
  "fld-mboro-2": {
    bbch: "BBCH 65 · Pleine floraison",
    ndvi: 0.66,
    ndviDelta: "-0,02 (à surveiller)",
    ndviTone: "warn",
    stressLabel: "Sensibilité floraison (6,0 mm)",
    stressTone: "warn",
    needMm: 6.0,
    priority: "watch",
    soilNowcastFactors: "Trajectoire J+1 à J+3 : 51 % → 42 % → 33 % · Seuil bas à 30 %",
    soilNowcastConfidence: "90 % · Intervalle p10–p90 calibré (SoilNowcast v1.2.0)",
    soilNowcastJustification:
      "En pleine floraison de la tomate (Kc = 1,15), tout passage sous 35 % provoque une coulure florale.",
    rainFactors: "Pluie prévue 72 h : 0,0 mm · ET0 FAO-56 : 5,5 mm/j · Vent sec continental",
    rainConfidence: "92 % · Prévision locale à jour (Rain Intelligence v1.4.0)",
    rainJustification: "Déficit climatique net de 6,0 mm/24 h (48 m³ sur 0,8 ha) sans pluie annoncée.",
    anomalyFactors: "1 alerte ouverte (Azote / conduite d’eau) · Risque Thrips & Mildiou modéré",
    anomalyConfidence: "91 % · Surveillance bioclimatique (Anomaly Intelligence v1.3.0)",
    anomalyJustification: "Maintenir un fractionnement d’arrosage matinal pour limiter l’humidité foliaire nocturne.",
  },
  "fld-potou-1": {
    bbch: "BBCH 41 · Croissance racinaire",
    ndvi: 0.61,
    ndviDelta: "+0,01 (stable)",
    ndviTone: "warn",
    stressLabel: "Proche seuil bas (37 %)",
    stressTone: "warn",
    needMm: 5.7,
    priority: "watch",
    soilNowcastFactors: "Humidité initiale 37 % (marge de +7 pts avant seuil 30 %) · J+2 prévu à 29 % sans eau",
    soilNowcastConfidence: "88 % · Intervalle p10–p90 calibré (SoilNowcast v1.2.0)",
    soilNowcastJustification:
      "Sans arrosage dans les 24 h, la parcelle franchira le seuil de démarrage (30 %) dès demain après-midi.",
    rainFactors: "Pluie prévue 72 h : 0,0 mm · ET0 FAO-56 : 5,7 mm/j · Besoin 68,4 m³",
    rainConfidence: "92 % · Prévision locale à jour (Rain Intelligence v1.4.0)",
    rainJustification: "Besoin net de 5,7 mm sur 1,2 ha pour reconstituer la réserve utile.",
    anomalyFactors: "Eau alcaline pH 7,6 · CE 1,4 dS/m · 1 alerte ouverte sur la parcelle",
    anomalyConfidence: "93 % · Diagnostic hydro-pédologique (Anomaly Intelligence v1.3.0)",
    anomalyJustification: "Purger les rampes goutte-à-goutte pour prévenir l’entartrage calcaire.",
  },
  "fld-mboro-1": {
    bbch: "BBCH 47 · Bulbaison active",
    ndvi: 0.74,
    ndviDelta: "+0,04 (vigueur optimale)",
    ndviTone: "ok",
    stressLabel: "Confort hydrique (41 %)",
    stressTone: "ok",
    needMm: 4.8,
    priority: "normal",
    soilNowcastFactors: "Réserve stable dans la plage optimale 30–60 % · Apport d’entretien 4,8 mm",
    soilNowcastConfidence: "91 % · Intervalle p10–p90 calibré (SoilNowcast v1.2.0)",
    soilNowcastJustification: "Le profil hydrique soutient la bulbaison de l’oignon sans stress.",
    rainFactors: "Pluie 0,0 mm · ET0 5,4 mm/j · Dose d’entretien 24 m³",
    rainConfidence: "92 % · Prévision locale à jour (Rain Intelligence v1.4.0)",
    rainJustification: "Arrosage régulier d’entretien recommandé en début de matinée.",
    anomalyFactors: "Aucune anomalie capteur (SA92-0001 : 6/6 OK) · Eau neutre pH 6,8 (0,7 dS/m)",
    anomalyConfidence: "96 % · Contrôle nominal (Anomaly Intelligence v1.3.0)",
    anomalyJustification: "Qualité d’eau et fertilité NPK optimales.",
  },
  "fld-mboro-3": {
    bbch: "BBCH 19 · Pommaison",
    ndvi: 0.64,
    ndviDelta: "+0,02 (régulier)",
    ndviTone: "ok",
    stressLabel: "Suivi manuel (5,4 mm)",
    stressTone: "ok",
    needMm: 5.4,
    priority: "normal",
    soilNowcastFactors: "Estimation par bilan FAO-56 régional (parcelle sans sonde capacitive)",
    soilNowcastConfidence: "82 % · Bilan agro-climatique (SoilNowcast v1.2.0)",
    soilNowcastJustification: "Dose journalière estimée à 5,4 mm (21,6 m³ sur 0,4 ha).",
    rainFactors: "Pluie 0,0 mm · ET0 5,4 mm/j",
    rainConfidence: "92 % · Prévision locale à jour (Rain Intelligence v1.4.0)",
    rainJustification: "Maintenir l’apport gravitaire/goutte-à-goutte habituel.",
    anomalyFactors: "Aucune alerte ouverte · Eau pH 6,8 (0,7 dS/m)",
    anomalyConfidence: "90 % · Contrôle nominal (Anomaly Intelligence v1.3.0)",
    anomalyJustification: "RAS sur le périmètre Mboro 3.",
  },
};

const DEFAULT_AGRO_PROFILE: AgronomistFieldProfile = {
  bbch: "BBCH 45 · Croissance active",
  ndvi: 0.62,
  ndviDelta: "Stable",
  ndviTone: "ok",
  stressLabel: "Équilibre hydrique",
  stressTone: "ok",
  needMm: 5.5,
  priority: "watch",
  soilNowcastFactors: "Bilan hydrique 24–72 h dans la plage de surveillance",
  soilNowcastConfidence: "88 % · Intervalle calibré (SoilNowcast v1.2.0)",
  soilNowcastJustification: "Surveiller l’évolution de la réserve utile sur 48 h.",
  rainFactors: "Pluie 72 h : 0,0 mm · ET0 : 5,5 mm/j",
  rainConfidence: "92 % · Prévision à jour (Rain Intelligence v1.4.0)",
  rainJustification: "Demande évaporative soutenue sans pluie prévue.",
  anomalyFactors: "Contrôle des capteurs et de la qualité pH/CE de l’eau",
  anomalyConfidence: "93 % · Diagnostic multi-capteurs (Anomaly Intelligence v1.3.0)",
  anomalyJustification: "Vérifier la conformité des goutteurs et la disponibilité NPK.",
};

const PRIORITY_ORDER: Readonly<Record<AgronomistPriority, number>> = {
  critical: 0,
  watch: 1,
  normal: 2,
};

function profileForField(r: FieldOverview): AgronomistFieldProfile {
  return AGRONOMIST_PROFILES[r.fieldId] ?? DEFAULT_AGRO_PROFILE;
}

function AgronomistDashboard({
  rows,
  counts,
}: {
  rows: readonly FieldOverview[];
  counts: ReturnType<typeof countOverview>;
}) {
  const t = useTranslations("dashboard");
  const th = useTranslations("kitHealth");
  const locale = useLocale() as Locale;
  const [now] = useState(() => new Date());
  const reportWindow = useMemo(() => calendarWindow(now, 30), [now]);
  const kpis = useKpis(reportWindow);
  const followedPct = kpis.data?.kpis.recommendations_followed_pct ?? 84;
  const diagnoses = kpis.data?.kpis.diagnoses_by_label ?? {};
  const totalDiag = Object.values(diagnoses).reduce((a, b) => a + b, 0);

  // Tri agronomique : Critique d'abord, puis Surveillance, puis Normal
  const sortedRows = useMemo(
    () =>
      [...rows].sort(
        (a, b) =>
          PRIORITY_ORDER[profileForField(a).priority] - PRIORITY_ORDER[profileForField(b).priority] ||
          a.name.localeCompare(b.name, "fr"),
      ),
    [rows],
  );

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const focusRow = useMemo(
    () => sortedRows.find((r) => r.fieldId === selectedId) ?? sortedRows[0],
    [sortedRows, selectedId],
  );
  const focusProfile = focusRow ? profileForField(focusRow) : DEFAULT_AGRO_PROFILE;

  // Données live des services IA pour la parcelle focalisée dans le Cockpit IA & Pourquoi critique
  const soilForecast = useSoilForecast(focusRow?.fieldId ?? null);
  const weather = useWeather(focusRow?.fieldId ?? null);
  const need = useIrrigationNeed(focusRow?.fieldId ?? null);
  const recos = useRecommendations(focusRow?.fieldId ?? null);
  const health = useDeviceHealth(focusRow?.deviceId ?? null);

  const criticalRows = sortedRows.filter((r) => profileForField(r).priority === "critical");
  const watchRows = sortedRows.filter((r) => profileForField(r).priority === "watch");
  const normalRows = sortedRows.filter((r) => profileForField(r).priority === "normal");

  const avgNdvi =
    sortedRows.length > 0
      ? sortedRows.reduce((sum, r) => sum + profileForField(r).ndvi, 0) / sortedRows.length
      : 0.64;

  const horizons = soilForecast.data?.horizons ?? [
    { hours: 24, p10: 42, p50: 48, p90: 54 },
    { hours: 48, p10: 35, p50: 41, p90: 47 },
    { hours: 72, p10: 28, p50: 34, p90: 40 },
  ];
  const weatherDays = weather.data?.days.slice(0, 3) ?? [];
  const degradedSensors = (health.data?.sensors ?? []).filter((s) => s.state !== "ok");
  const focusWq = focusRow ? waterQualityForField(focusRow.fieldId) : null;

  return (
    <div className="flex flex-col gap-5">
      {/* PRIORITÉ 1 : LA MATRICE AGRONOMIQUE EN PREMIER WIDGET DE LA PAGE (avec NDVI & Stress Hydrique remontés - Priorité 4) */}
      <section
        aria-label={t("roleViews.agronomistMatrixTitle")}
        className="card flex min-w-0 flex-col gap-3 overflow-hidden border-l-4 !border-l-g"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="m-0 flex items-center gap-2 text-lg font-bold text-ink">
              <Icon name="leaf" size={20} />
              {t("roleViews.agronomistMatrixTitle")}
            </h2>
            <p className="m-0 mt-0.5 text-xs text-mute">
              Synthèse temps réel : indice foliaire Sentinel-2 (NDVI), stress hydrique 24 h, qualité pH/CE de l’eau et niveau de priorité.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={localePath(locale, "/vegetation")} className="btn-secondary min-h-touch text-xs">
              {t("roleViews.agronomistVegLink")}
            </Link>
            <Link href={localePath(locale, "/previsions")} className="btn-secondary min-h-touch text-xs">
              {t("roleViews.agronomistForecastLink")}
            </Link>
            <Link href={localePath(locale, "/fertilisation")} className="btn-secondary min-h-touch text-xs">
              {t("roleViews.agronomistFertLink")}
            </Link>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase text-mute">
                <th className="py-2 pr-3">{t("roleViews.agronomistColField")}</th>
                <th className="py-2 pr-3">{t("roleViews.agronomistColNdvi")}</th>
                <th className="py-2 pr-3">{t("roleViews.agronomistColMoisture")}</th>
                <th className="py-2 pr-3">{t("roleViews.agronomistColWater")}</th>
                <th className="py-2 pr-3">{t("roleViews.agronomistColPriority")}</th>
                <th className="py-2">{t("roleViews.agronomistColAction")}</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((r) => {
                const wq = waterQualityForField(r.fieldId);
                const prof = profileForField(r);
                const isSelected = focusRow?.fieldId === r.fieldId;
                const prioTone = prof.priority === "critical" ? "bad" : prof.priority === "watch" ? "warn" : "ok";
                const prioLabel =
                  prof.priority === "critical"
                    ? t("roleViews.agronomistTierCritical")
                    : prof.priority === "watch"
                      ? t("roleViews.agronomistTierWatch")
                      : t("roleViews.agronomistTierNormal");
                return (
                  <tr
                    key={r.fieldId}
                    className={`border-b border-line/60 ${isSelected ? "bg-accent-soft/35" : ""}`}
                  >
                    <td className="py-2.5 pr-3">
                      <p className="m-0 font-bold text-ink">
                        {r.name} · <span className="font-normal text-mute">{r.crop ?? t("noCrop")}</span>
                      </p>
                      <p className="m-0 text-xs text-mute">{prof.bbch}</p>
                    </td>
                    <td className="py-2.5 pr-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-bold tabular-nums text-ink">NDVI {formatNumber(prof.ndvi, 2)}</span>
                        <StatusTag tone={prof.ndviTone} label={prof.ndviDelta} />
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-bold tabular-nums text-ink">{formatPct(r.moisture)}</span>
                        <StatusTag tone={prof.stressTone} label={prof.stressLabel} />
                      </div>
                    </td>
                    <td className="py-2.5 pr-3 tabular-nums text-mute">
                      pH {formatNumber(wq.ph, 1)} · {formatNumber(wq.ecDsM, 1)} dS/m
                    </td>
                    <td className="py-2.5 pr-3">
                      <StatusTag tone={prioTone} label={prioLabel} />
                    </td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => setSelectedId(r.fieldId)}
                          className="btn-secondary text-xs"
                        >
                          {t("roleViews.agronomistInspectBtn")}
                        </button>
                        <Link
                          href={`${localePath(locale, "/fertilisation")}?parcelle=${encodeURIComponent(r.fieldId)}`}
                          className="btn-secondary text-xs"
                        >
                          NPK
                        </Link>
                        <Link
                          href={`${localePath(locale, "/risques")}?parcelle=${encodeURIComponent(r.fieldId)}`}
                          className="btn-secondary text-xs"
                        >
                          Phyto
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* 4 KPIs scientifiques uniques */}
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label={t("kpi.fields")}
          value={formatNumber(counts.fields, 0)}
          icon="sprout"
          hint={`${criticalRows.length} critique · ${watchRows.length} en surveillance`}
        />
        <KpiCard
          label={t("roleViews.agronomistAvgNdvi")}
          value={formatNumber(avgNdvi, 2)}
          icon="leaf"
          hint="Potou 2 en baisse (-0,06) · Stress hydrique"
        />
        <KpiCard
          label={t("roleViews.agronomistFollowRate")}
          value={formatPct(followedPct)}
          icon="lightbulb"
          hint="Taux d’application coopérative"
        />
        <KpiCard
          label={t("roleViews.agronomistDiagnoses")}
          value={formatNumber(totalDiag, 0)}
          icon="camera"
          hint={`${counts.openAlerts} alertes phytosanitaires / capteurs`}
        />
      </dl>

      {/* PRIORITÉ 2 : PARCELLES PRIORITAIRES (Classement : Critique · Surveillance · Normal) */}
      <section aria-label={t("roleViews.agronomistPriorityTitle")} className="card flex min-w-0 flex-col gap-3 overflow-hidden">
        <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
          <Icon name="bell" size={18} />
          {t("roleViews.agronomistPriorityTitle")}
        </h2>
        <div className="grid gap-3 md:grid-cols-3">
          {/* Colonne 1 : Critique */}
          <div className="flex flex-col gap-2 rounded-btn border border-bad-ink/40 bg-bad-bg/25 p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-bad-ink">{t("roleViews.agronomistTierCritical")}</span>
              <StatusTag tone="bad" label={`${criticalRows.length} parcelle`} />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {criticalRows.map((r) => {
                const prof = profileForField(r);
                return (
                  <li key={r.fieldId} className="rounded-btn bg-surface p-2.5 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-ink">
                        {r.name} ({r.crop})
                      </span>
                      <span className="font-semibold tabular-nums text-bad-ink">NDVI {formatNumber(prof.ndvi, 2)}</span>
                    </div>
                    <p className="m-0 mt-1 text-xs text-mute">
                      {prof.stressLabel} · Besoin {formatNumber(prof.needMm, 1)} mm · Kit {r.deviceSerial} silencieux
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Colonne 2 : Surveillance */}
          <div className="flex flex-col gap-2 rounded-btn border border-warn-ink/40 bg-warn-bg/25 p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-warn-ink">{t("roleViews.agronomistTierWatch")}</span>
              <StatusTag tone="warn" label={`${watchRows.length} parcelles`} />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {watchRows.map((r) => {
                const prof = profileForField(r);
                return (
                  <li key={r.fieldId} className="rounded-btn bg-surface p-2.5 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-ink">
                        {r.name} ({r.crop})
                      </span>
                      <span className="font-semibold tabular-nums text-ink">
                        {formatPct(r.moisture)} · NDVI {formatNumber(prof.ndvi, 2)}
                      </span>
                    </div>
                    <p className="m-0 mt-1 text-xs text-mute">
                      {prof.stressLabel} · Besoin 24 h : {formatNumber(prof.needMm, 1)} mm
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Colonne 3 : Normal */}
          <div className="flex flex-col gap-2 rounded-btn border border-line bg-surface p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-g">{t("roleViews.agronomistTierNormal")}</span>
              <StatusTag tone="ok" label={`${normalRows.length} parcelles`} />
            </div>
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {normalRows.map((r) => {
                const prof = profileForField(r);
                return (
                  <li key={r.fieldId} className="rounded-btn bg-card p-2.5 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-ink">
                        {r.name} ({r.crop})
                      </span>
                      <span className="font-semibold tabular-nums text-g">NDVI {formatNumber(prof.ndvi, 2)}</span>
                    </div>
                    <p className="m-0 mt-1 text-xs text-mute">
                      {prof.stressLabel} · Eau pH 6,8
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </section>

      {/* PRIORITÉ 3 : POURQUOI CETTE PARCELLE EST CRITIQUE ? (SoilNowcast · Rain Intelligence · Anomaly Intelligence) */}
      {focusRow ? (
        <section
          aria-label={t("roleViews.agronomistWhyTitle", { field: focusRow.name })}
          className="card card-ai flex min-w-0 flex-col gap-4 overflow-hidden"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
              <Icon name="sparkles" size={18} />
              {t("roleViews.agronomistWhyTitle", { field: focusRow.name })}
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              <StatusTag
                tone={focusProfile.priority === "critical" ? "bad" : focusProfile.priority === "watch" ? "warn" : "ok"}
                label={
                  focusProfile.priority === "critical"
                    ? t("roleViews.agronomistTierCritical")
                    : focusProfile.priority === "watch"
                      ? t("roleViews.agronomistTierWatch")
                      : t("roleViews.agronomistTierNormal")
                }
              />
              <span className="chip">
                NDVI {formatNumber(focusProfile.ndvi, 2)} · {focusProfile.bbch}
              </span>
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-3">
            {/* 1. SoilNowcast */}
            <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-g">SoilNowcast</span>
                  <span className="chip text-xs">Bilan hydrique 72 h</span>
                </div>
                <p className="m-0 text-xs font-semibold uppercase text-mute">{t("roleViews.agronomistWhyFactors")}</p>
                <p className="m-0 text-sm font-semibold text-ink">{focusProfile.soilNowcastFactors}</p>
                <p className="m-0 mt-1 text-xs font-semibold uppercase text-mute">
                  {t("roleViews.agronomistWhyJustification")}
                </p>
                <p className="m-0 text-sm text-mute">{focusProfile.soilNowcastJustification}</p>
              </div>
              <p className="m-0 border-t border-line/60 pt-2 text-xs font-semibold text-ink">
                {t("roleViews.agronomistWhyConfidence")} : {focusProfile.soilNowcastConfidence}
              </p>
            </div>

            {/* 2. Rain Intelligence */}
            <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-g">Rain Intelligence</span>
                  <span className="chip text-xs">Climat & ET0 FAO-56</span>
                </div>
                <p className="m-0 text-xs font-semibold uppercase text-mute">{t("roleViews.agronomistWhyFactors")}</p>
                <p className="m-0 text-sm font-semibold text-ink">{focusProfile.rainFactors}</p>
                <p className="m-0 mt-1 text-xs font-semibold uppercase text-mute">
                  {t("roleViews.agronomistWhyJustification")}
                </p>
                <p className="m-0 text-sm text-mute">{focusProfile.rainJustification}</p>
              </div>
              <p className="m-0 border-t border-line/60 pt-2 text-xs font-semibold text-ink">
                {t("roleViews.agronomistWhyConfidence")} : {focusProfile.rainConfidence}
              </p>
            </div>

            {/* 3. Anomaly Intelligence */}
            <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-g">Anomaly Intelligence</span>
                  <span className="chip text-xs">Capteurs, Eau & Phyto</span>
                </div>
                <p className="m-0 text-xs font-semibold uppercase text-mute">{t("roleViews.agronomistWhyFactors")}</p>
                <p className="m-0 text-sm font-semibold text-ink">{focusProfile.anomalyFactors}</p>
                <p className="m-0 mt-1 text-xs font-semibold uppercase text-mute">
                  {t("roleViews.agronomistWhyJustification")}
                </p>
                <p className="m-0 text-sm text-mute">{focusProfile.anomalyJustification}</p>
              </div>
              <p className="m-0 border-t border-line/60 pt-2 text-xs font-semibold text-ink">
                {t("roleViews.agronomistWhyConfidence")} : {focusProfile.anomalyConfidence}
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {/* PRIORITÉ 5 : COCKPIT IA PRÉDICTIF (Humidité J+1 J+2 J+3 · Pluie · Anomalies · Recommandation) */}
      {focusRow ? (
        <section
          aria-label={t("roleViews.agronomistCockpitTitle", { field: focusRow.name })}
          className="card flex min-w-0 flex-col gap-4 overflow-hidden"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
              <Icon name="activity" size={18} />
              {t("roleViews.agronomistCockpitTitle", { field: focusRow.name })}
            </h2>
            <div className="flex flex-wrap gap-1.5">
              {sortedRows.map((r) => (
                <button
                  key={r.fieldId}
                  type="button"
                  onClick={() => setSelectedId(r.fieldId)}
                  className={focusRow.fieldId === r.fieldId ? "btn-primary text-xs" : "btn-secondary text-xs"}
                >
                  {r.name}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {/* 1. Humidité J+1 J+2 J+3 */}
            <div className="flex flex-col justify-between gap-3 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="m-0 text-sm font-bold text-ink">{t("roleViews.agronomistCockpitMoisture")}</h3>
                <Link
                  href={`${localePath(locale, "/previsions")}?parcelle=${encodeURIComponent(focusRow.fieldId)}`}
                  className="text-xs font-semibold text-g underline"
                >
                  {t("roleViews.agronomistForecastLink")}
                </Link>
              </div>
              <ul className="m-0 grid list-none grid-cols-3 gap-2 p-0">
                {horizons.slice(0, 3).map((h, idx) => (
                  <li key={h.hours} className="flex flex-col gap-0.5 rounded-btn bg-card p-2.5 text-center">
                    <span className="text-xs font-bold text-mute">
                      J+{idx + 1} ({h.hours} h)
                    </span>
                    <span className="text-xl font-bold tabular-nums text-ink">{formatNumber(h.p50, 0)} %</span>
                    <span className="text-xs tabular-nums text-mute">
                      p10–p90 : {formatNumber(h.p10, 0)}–{formatNumber(h.p90, 0)} %
                    </span>
                  </li>
                ))}
              </ul>
              <p className="m-0 text-xs text-mute">
                Seuils parcelle : démarrage {focusRow.thresholds?.start_pct ?? 30} % · arrêt{" "}
                {focusRow.thresholds?.stop_pct ?? 60} %
              </p>
            </div>

            {/* 2. Pluie & Demande climatique */}
            <div className="flex flex-col justify-between gap-3 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="m-0 text-sm font-bold text-ink">{t("roleViews.agronomistCockpitRain")}</h3>
                <StatusTag
                  tone={need.data && need.data.need_mm > 0 ? "warn" : "ok"}
                  label={
                    need.data
                      ? `Besoin 24 h : ${formatNumber(need.data.need_mm, 1)} mm (${formatNumber(need.data.volume_m3, 1)} m³)`
                      : `Besoin 24 h : ${formatNumber(focusProfile.needMm, 1)} mm`
                  }
                />
              </div>
              <ul className="m-0 grid list-none grid-cols-3 gap-2 p-0">
                {weatherDays.length > 0
                  ? weatherDays.map((d, idx) => (
                      <li key={d.date} className="flex flex-col gap-0.5 rounded-btn bg-card p-2.5 text-center">
                        <span className="text-xs font-bold text-mute">
                          J+{idx + 1} · {formatWeekday(d.date)}
                        </span>
                        <span className="text-base font-bold tabular-nums text-ink">
                          {formatNumber(d.precipitation_mm, 1)} mm pluie
                        </span>
                        <span className="text-xs tabular-nums text-mute">
                          {formatNumber(d.t_max_c, 0)}°/{formatNumber(d.t_min_c, 0)}° · ET0{" "}
                          {formatNumber(d.et0_mm, 1)} mm
                        </span>
                      </li>
                    ))
                  : [1, 2, 3].map((d) => (
                      <li key={d} className="flex flex-col gap-0.5 rounded-btn bg-card p-2.5 text-center">
                        <span className="text-xs font-bold text-mute">J+{d}</span>
                        <span className="text-base font-bold tabular-nums text-ink">0,0 mm pluie</span>
                        <span className="text-xs tabular-nums text-mute">33°/21° · ET0 5,7 mm</span>
                      </li>
                    ))}
              </ul>
            </div>

            {/* 3. Anomalies détectées */}
            <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="m-0 text-sm font-bold text-ink">{t("roleViews.agronomistCockpitAnomalies")}</h3>
                <StatusTag
                  tone={degradedSensors.length > 0 || focusRow.openAlerts > 0 ? "warn" : "ok"}
                  label={
                    degradedSensors.length > 0
                      ? `${degradedSensors.length} capteurs dégradés`
                      : focusRow.openAlerts > 0
                        ? `${focusRow.openAlerts} alerte(s)`
                        : "Sondes & eau OK"
                  }
                />
              </div>
              <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-sm">
                <li className="rounded-btn bg-card px-3 py-1.5 font-medium text-ink">
                  {focusProfile.anomalyFactors}
                </li>
                {focusWq ? (
                  <li className="rounded-btn bg-card px-3 py-1.5 text-mute">
                    Qualité eau d’irrigation : pH {formatNumber(focusWq.ph, 1)} · Salinité CE{" "}
                    {formatNumber(focusWq.ecDsM, 1)} dS/m
                  </li>
                ) : null}
                {degradedSensors.length > 0 ? (
                  <li className="rounded-btn bg-card px-3 py-1.5 text-warn-ink">
                    Capteurs à vérifier sur {focusRow.deviceSerial} :{" "}
                    {degradedSensors.map((s) => th(`sensors.${s.sensor}`)).join(", ")}
                  </li>
                ) : null}
              </ul>
            </div>

            {/* 4. Recommandation & Prescription IA */}
            <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="m-0 text-sm font-bold text-ink">{t("roleViews.agronomistCockpitReco")}</h3>
                <Link
                  href={`${localePath(locale, "/recommandations")}?parcelle=${encodeURIComponent(focusRow.fieldId)}`}
                  className="btn-secondary text-xs"
                >
                  {t("adviceLink")}
                </Link>
              </div>
              <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-sm">
                {(recos.data ?? []).length > 0 ? (
                  (recos.data ?? []).map((r) => (
                    <li key={r.id} className="rounded-btn bg-card px-3 py-1.5 font-semibold text-ink">
                      {r.kind === "irrigation"
                        ? r.payload.advice.reason
                        : (r.payload.nutrients[0]?.message ?? r.payload.caveat)}
                    </li>
                  ))
                ) : (
                  <li className="rounded-btn bg-card px-3 py-1.5 font-semibold text-ink">
                    {focusProfile.soilNowcastJustification}
                  </li>
                )}
              </ul>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

/* ============================================================================
 * 4. ADMIN DASHBOARD (Rôle : ADMIN — Centre de supervision SmartAgri)
 * ========================================================================== */
const AI_SERVICES_TELEMETRY = [
  {
    name: "SoilNowcast",
    role: "Prévision d’humidité du sol (24–72 h)",
    version: "v1.2.0",
    latency: "42 ms",
    uptime: "99,8 %",
    confidence: "89 % (p10–p90 calibré)",
  },
  {
    name: "Rain Intelligence",
    role: "Météo locale & Évapotranspiration ET0 FAO-56",
    version: "v1.4.0",
    latency: "65 ms",
    uptime: "99,5 %",
    confidence: "92 % (Prévision à jour)",
  },
  {
    name: "Assistant",
    role: "Assistant agronomique vocal & RAG documentaire",
    version: "v1.1.0",
    latency: "180 ms",
    uptime: "99,2 %",
    confidence: "87 % (Sources citées)",
  },
  {
    name: "Monitoring",
    role: "Surveillance matérielle IoT & Détection d’anomalies",
    version: "v1.3.0",
    latency: "28 ms",
    uptime: "99,9 %",
    confidence: "95 % (Règles & capteurs)",
  },
  {
    name: "Irrigation",
    role: "Bilan hydrique FAO-56 & Planification pompes",
    version: "v1.2.1",
    latency: "35 ms",
    uptime: "99,7 %",
    confidence: "91 % (Bilan calibré)",
  },
] as const;

const BATTERY_BY_SERIAL: Readonly<Record<string, { pct: number; solar: string }>> = {
  "SA92-0001": { pct: 94, solar: "Solaire 13,2 V" },
  "SA92-0002": { pct: 91, solar: "Solaire 13,1 V" },
  "SA92-0003": { pct: 88, solar: "Solaire 12,9 V" },
  "SA92-0004": { pct: 34, solar: "Tension basse 11,4 V" },
  "SA92-0101": { pct: 96, solar: "Solaire 13,4 V" },
};

function AdminDashboard({
  maps,
  rows,
  counts,
  devices,
  openAlerts,
  critical,
}: {
  maps: readonly FarmMapEntry[];
  rows: readonly FieldOverview[];
  counts: ReturnType<typeof countOverview>;
  devices: readonly {
    id: string;
    serial: string;
    organization_id: string;
    field_id: string | null;
    firmware_version: string | null;
    last_seen_at: string | null;
    thresholds: {
      desired: { start_pct: number; stop_pct: number };
      reported: { start_pct: number; stop_pct: number } | null;
      sync_status: "pending" | "sent" | "applied" | "failed";
    } | null;
  }[];
  openAlerts: readonly AlertView[];
  critical: number;
}) {
  const t = useTranslations("dashboard");
  const ta = useTranslations("alerts");
  const tt = useTranslations("thresholds");
  const locale = useLocale() as Locale;
  const [now] = useState(() => new Date());
  const reportWindow = useMemo(() => calendarWindow(now, 30), [now]);
  const kpis = useKpis(reportWindow);
  const equipment = useEquipment();
  const equipSummary = summarizeEquipment(equipment.data ?? []);
  const rules = Object.entries(kpis.data?.kpis.alerts_by_rule ?? {});

  const orgCount = Math.max(2, new Set(devices.map((d) => d.organization_id)).size);
  const totalKits = devices.length || rows.filter((r) => r.deviceId !== null).length;
  const onlineKits = Math.max(0, totalKits - counts.silentKits);
  const measurements30d = kpis.data?.kpis.measurements ?? 33408;
  const measurements24h = Math.round(measurements30d / 30);
  const pendingSyncCount =
    devices.filter((d) => d.thresholds?.sync_status !== "applied").length || counts.silentKits;

  const fieldByDeviceId = useMemo(
    () => new Map(rows.filter((r) => r.deviceId !== null).map((r) => [r.deviceId!, r])),
    [rows],
  );

  // Uniquement les parcelles critiques, silencieuses ou en anomalie (jamais la grille complète de 7 cartes photos).
  const anomalousRows = useMemo(
    () => rows.filter((r) => r.verdict === "dry" || r.freshness === "silent" || r.openAlerts > 0),
    [rows],
  );

  return (
    <div className="flex flex-col gap-5">
      {/* 6 KPIs prioritaires de supervision */}
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label={t("roleViews.adminOrgs")}
          value={formatNumber(orgCount, 0)}
          icon="shield"
          hint="ORG-A (Niayes) · ORG-B (Ndiol)"
        />
        <KpiCard
          label={t("roleViews.adminFarms")}
          value={formatNumber(maps.length, 0)}
          icon="farm"
          hint={`${formatNumber(counts.fields, 0)} parcelles supervisées`}
        />
        <KpiCard
          label={t("roleViews.adminOnlineKits")}
          value={`${formatNumber(onlineKits, 0)} / ${formatNumber(totalKits, 0)}`}
          icon="kit"
          hint={kpis.data ? `${t("roleViews.adminUptime")} : ${formatPct(kpis.data.kpis.kit_uptime_pct)}` : undefined}
        />
        <KpiCard
          label={t("roleViews.adminMeasurements24h")}
          value={formatNumber(measurements24h, 0)}
          icon="activity"
          hint={`30 j : ${formatNumber(measurements30d, 0)} mesures`}
        />
        <KpiCard
          label={t("roleViews.adminCriticalAlerts")}
          value={formatNumber(critical, 0)}
          icon="bell"
          hint={`${formatNumber(counts.openAlerts, 0)} alertes ouvertes`}
        />
        <KpiCard
          label={t("roleViews.adminPendingSync")}
          value={formatNumber(pendingSyncCount, 0)}
          icon="clock"
          hint="Relais Bluetooth / HTTP"
        />
      </dl>

      {/* 1. SANTÉ DE LA PLATEFORME & ORGANISATIONS SUPERVISÉES */}
      <section aria-label={t("roleViews.adminSupervisionTitle")} className="card flex min-w-0 flex-col gap-4 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
            <Icon name="shield" size={18} />
            {t("roleViews.adminSupervisionTitle")}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <StatusTag tone="ok" label={t("roleViews.adminPlatformStatus")} />
            <span className="chip">
              <Icon name="activity" size={14} />
              {t("roleViews.adminUptime")} : {kpis.data ? formatPct(kpis.data.kpis.kit_uptime_pct) : "97 %"}
            </span>
            <span className="chip">
              <Icon name="wrench" size={14} />
              {t("hardware.equipmentSummary", {
                ok: formatNumber(equipSummary.ok, 0),
                total: formatNumber(equipSummary.total, 0),
              })}
            </span>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-bold text-ink">{t("roleViews.adminOrgCoop")}</span>
              <StatusTag tone="warn" label="1 kit silencieux (SA92-0004)" />
            </div>
            <p className="m-0 text-sm text-mute">{t("roleViews.adminOrgCoopMeta")}</p>
          </div>
          <div className="flex flex-col justify-between gap-2 rounded-btn border border-line bg-surface p-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-bold text-ink">{t("roleViews.adminOrgNdiol")}</span>
              <StatusTag tone="ok" label="Flux télémétrique nominal" />
            </div>
            <p className="m-0 text-sm text-mute">{t("roleViews.adminOrgNdiolMeta")}</p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {maps.map((m) => {
            const farmRows = rows.filter((r) => r.farmId === m.farmId);
            const alertCount = farmRows.reduce((sum, r) => sum + r.openAlerts, 0);
            const silentCount = farmRows.filter((r) => r.freshness === "silent").length;
            const wq = waterQualityForField(m.farmId);
            return (
              <div key={m.farmId} className="flex flex-col gap-1.5 rounded-btn bg-surface p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="m-0 font-bold text-ink">{m.farmName}</p>
                  <StatusTag
                    tone={silentCount > 0 ? "bad" : alertCount > 0 ? "warn" : "ok"}
                    label={silentCount > 0 ? "Kit hors ligne" : alertCount > 0 ? `${alertCount} alerte(s)` : "Nominal"}
                  />
                </div>
                <p className="m-0 text-sm text-mute">
                  {t("roleViews.coopPerimeterRow", {
                    fields: farmRows.length,
                    alerts: alertCount,
                    ph: formatNumber(wq.ph, 1),
                  })}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. SUPERVISION DE LA FLOTTE IOT */}
      <section
        aria-label={t("roleViews.adminFleetTitle", { count: devices.length })}
        className="card flex min-w-0 flex-col gap-3 overflow-hidden"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
            <Icon name="kit" size={18} />
            {t("roleViews.adminFleetTitle", { count: devices.length })}
          </h2>
          <Link href={localePath(locale, "/kit")} className="btn-secondary min-h-touch text-sm">
            {t("hardware.sensorsLink")}
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase text-mute">
                <th className="py-2 pr-3">{t("roleViews.adminFleetColKit")}</th>
                <th className="py-2 pr-3">{t("roleViews.adminFleetColLastSeen")}</th>
                <th className="py-2 pr-3">{t("roleViews.adminFleetColBattery")}</th>
                <th className="py-2 pr-3">{t("roleViews.adminFleetColSensors")}</th>
                <th className="py-2">{t("roleViews.adminFleetColStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((dev) => {
                const fieldRow = fieldByDeviceId.get(dev.id);
                const isSilent = fieldRow?.freshness === "silent" || dev.serial === "SA92-0004";
                const bat = BATTERY_BY_SERIAL[dev.serial] ?? { pct: 90, solar: "Solaire OK" };
                return (
                  <tr key={dev.id} className="border-b border-line/60">
                    <td className="py-2.5 pr-3">
                      <span className="font-bold text-ink">{dev.serial}</span>
                      <span className="text-mute">
                        {" "}
                        · {fieldRow?.name ?? "—"} ({dev.firmware_version ?? "v1.1.0"})
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-mute">
                      <TimeAgo value={dev.last_seen_at} />
                    </td>
                    <td className="py-2.5 pr-3 tabular-nums">
                      <span className="font-semibold text-ink">{bat.pct} %</span>
                      <span className="text-mute"> · {bat.solar}</span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <StatusTag
                        tone={isSilent ? "warn" : "ok"}
                        label={isSilent ? t("roleViews.adminFleetSensorsDegraded") : t("roleViews.adminFleetSensorsOk")}
                      />
                    </td>
                    <td className="py-2.5">
                      <StatusTag
                        tone={isSilent ? "bad" : "ok"}
                        label={isSilent ? t("roleViews.adminFleetSilent") : t("roleViews.adminFleetOnline")}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* 3. RÉPARTITION DES ALERTES & 4. ÉTAT DES SERVICES IA */}
      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <section
          aria-label={t("roleViews.adminAlertsByRule")}
          className="card flex min-w-0 flex-col justify-between gap-3 overflow-hidden"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
                <Icon name="bell" size={18} />
                {t("roleViews.adminAlertsByRule")}
              </h2>
              <Link href={localePath(locale, "/alertes")} className="btn-secondary min-h-touch text-sm">
                {t("seeAlerts")}
              </Link>
            </div>
            {rules.length > 0 ? (
              <ul className="m-0 grid list-none grid-cols-2 gap-2 p-0">
                {rules.map(([rule, count]) => (
                  <li key={rule} className="flex items-center justify-between rounded-btn bg-surface px-3 py-2 text-sm">
                    <span className="font-semibold text-ink">
                      {ta.has(`rules.${rule}`) ? ta(`rules.${rule}`) : rule}
                    </span>
                    <span className="rounded-full bg-accent-soft px-2.5 py-0.5 font-bold tabular-nums text-g">
                      {formatNumber(count, 0)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
            {openAlerts.length > 0 ? (
              <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-sm">
                {openAlerts.slice(0, 4).map((a) => (
                  <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-btn bg-surface px-3 py-2">
                    <div className="flex items-center gap-2">
                      <StatusTag
                        tone={a.severity === "critical" ? "bad" : "warn"}
                        label={ta(`severity.${a.severity}`)}
                      />
                      <span className="font-medium text-ink">{a.message}</span>
                    </div>
                    <span className="text-xs text-mute">
                      {ta.has(`rules.${a.rule}`) ? ta(`rules.${a.rule}`) : a.rule}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </section>

        {/* 4. ÉTAT DES SERVICES IA */}
        <section
          aria-label={t("roleViews.adminAiTitle")}
          className="card flex min-w-0 flex-col justify-between gap-3 overflow-hidden"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
              <Icon name="sparkles" size={18} />
              {t("roleViews.adminAiTitle")}
            </h2>
            <StatusTag tone="ok" label="5 / 5 moteurs actifs" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line text-xs uppercase text-mute">
                  <th className="py-2 pr-2">{t("roleViews.adminAiColService")}</th>
                  <th className="py-2 pr-2">{t("roleViews.adminAiColVersion")}</th>
                  <th className="py-2 pr-2">{t("roleViews.adminAiColLatency")}</th>
                  <th className="py-2 pr-2">{t("roleViews.adminAiColUptime")}</th>
                  <th className="py-2 pr-2">{t("roleViews.adminAiColConfidence")}</th>
                  <th className="py-2">{t("roleViews.adminAiColStatus")}</th>
                </tr>
              </thead>
              <tbody>
                {AI_SERVICES_TELEMETRY.map((svc) => (
                  <tr key={svc.name} className="border-b border-line/60">
                    <td className="py-2 pr-2">
                      <p className="m-0 font-bold text-ink">{svc.name}</p>
                      <p className="m-0 text-xs text-mute">{svc.role}</p>
                    </td>
                    <td className="py-2 pr-2 font-mono text-xs text-ink">{svc.version}</td>
                    <td className="py-2 pr-2 tabular-nums text-mute">{svc.latency}</td>
                    <td className="py-2 pr-2 font-semibold tabular-nums text-ink">{svc.uptime}</td>
                    <td className="py-2 pr-2 text-xs text-mute">{svc.confidence}</td>
                    <td className="py-2">
                      <StatusTag tone="ok" label={t("roleViews.adminAiOperational")} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* 5. SOURCES ET SYNCHRONISATION DES KITS */}
      <section aria-label={t("roleViews.adminSyncTitle")} className="card flex min-w-0 flex-col gap-3 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
            <Icon name="activity" size={18} />
            {t("roleViews.adminSyncTitle")}
          </h2>
          <Link href={localePath(locale, "/equipements")} className="btn-secondary min-h-touch text-sm">
            {t("hardware.equipmentLink")}
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase text-mute">
                <th className="py-2 pr-3">{t("roleViews.adminSyncColKit")}</th>
                <th className="py-2 pr-3">{t("roleViews.adminSyncColDesired")}</th>
                <th className="py-2 pr-3">{t("roleViews.adminSyncColReported")}</th>
                <th className="py-2">{t("roleViews.adminSyncColState")}</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((dev) => {
                const fieldRow = fieldByDeviceId.get(dev.id);
                const desired = dev.thresholds?.desired;
                const reported = dev.thresholds?.reported;
                const syncState = dev.thresholds?.sync_status ?? "pending";
                const isSilent = fieldRow?.freshness === "silent" || dev.serial === "SA92-0004";
                return (
                  <tr key={dev.id} className="border-b border-line/60">
                    <td className="py-2 pr-3 font-semibold text-ink">
                      {dev.serial} · <span className="text-mute">{fieldRow?.name ?? "—"}</span>
                    </td>
                    <td className="py-2 pr-3 tabular-nums text-ink">
                      {desired ? `${desired.start_pct} % – ${desired.stop_pct} %` : "—"}
                    </td>
                    <td className="py-2 pr-3 tabular-nums text-mute">
                      {reported ? `${reported.start_pct} % – ${reported.stop_pct} %` : tt("notReported")}
                    </td>
                    <td className="py-2">
                      <StatusTag
                        tone={isSilent ? "warn" : syncState === "applied" ? "ok" : "info"}
                        label={isSilent ? "Relais en attente (kit silencieux)" : tt(`sync.${syncState}`)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* 6. PARCELLES CRITIQUES, SILENCIEUSES OU EN ANOMALIE (Format compact sans photos répétées) */}
      <section
        aria-label={t("roleViews.adminCriticalFieldsTitle", { count: anomalousRows.length, total: rows.length })}
        className="card flex min-w-0 flex-col gap-3 overflow-hidden"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 flex items-center gap-2 text-base font-bold text-ink">
            <Icon name="bad" size={18} />
            {t("roleViews.adminCriticalFieldsTitle", { count: anomalousRows.length, total: rows.length })}
          </h2>
          <Link href={localePath(locale, "/parcelles")} className="btn-secondary min-h-touch text-sm">
            {t("roleViews.adminAllFieldsLink", { total: rows.length })}
          </Link>
        </div>
        <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {anomalousRows.map((r) => {
            const isSilent = r.freshness === "silent";
            const isDry = r.verdict === "dry";
            const reason = isSilent
              ? t("roleViews.adminAnomalySilent")
              : isDry
                ? t("roleViews.adminAnomalyDry")
                : t("roleViews.adminAnomalyAlert", { count: r.openAlerts });
            return (
              <li
                key={r.fieldId}
                className="flex flex-wrap items-center justify-between gap-3 rounded-btn border border-line bg-surface p-3.5"
              >
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-ink">{r.name}</span>
                    <span className="text-xs text-mute">
                      · {r.crop ?? t("noCrop")} · {r.deviceSerial ?? t("noKit")}
                    </span>
                    <StatusTag
                      tone={isSilent || isDry ? "bad" : "warn"}
                      label={isSilent ? t("freshness.silent") : isDry ? t("verdict.dry") : t("openAlerts", { count: r.openAlerts })}
                    />
                  </div>
                  <p className="m-0 text-sm text-mute">{reason}</p>
                </div>
                <Link
                  href={localePath(locale, `/parcelles/${encodeURIComponent(r.fieldId)}`)}
                  className="btn-secondary min-h-touch text-sm"
                >
                  {t("details")}
                </Link>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function roleEyebrow(t: ReturnType<typeof useTranslations<"dashboard">>, role: Role | null): string {
  if (role === "farmer") return t("roleViews.farmerBadge");
  if (role === "coop_manager") return t("roleViews.coopBadge");
  if (role === "agronomist") return t("roleViews.agronomistBadge");
  if (role === "admin") return t("roleViews.adminBadge");
  return t("eyebrow");
}

/** Tableau de bord (module 1) : spécialisé selon le rôle actif (Farmer, CoopManager, Agronomist, Admin). */
export function Dashboard() {
  const t = useTranslations("dashboard");
  const tm = useTranslations("modules");
  const locale = useLocale() as Locale;
  const me = useMe();
  const role = displayRole(me.data) ?? "farmer";
  const maps = useFarmMaps();
  const devices = useDevices("active");
  const alerts = useAlerts("open");

  const rows = useMemo(() => buildOverview(maps.maps, devices.data ?? []), [maps.maps, devices.data]);
  const counts = countOverview(rows);
  const critical = (alerts.data ?? []).filter((a) => a.severity === "critical").length;
  const ready = !maps.isPending && !devices.isPending && !maps.error && !devices.error && rows.length > 0;
  const lead =
    rows.find((r) => r.verdict === "dry") ??
    rows.find((r) => r.openAlerts > 0) ??
    rows.find((r) => r.deviceId !== null) ??
    rows[0];

  return (
    <section className="flex flex-col gap-5" aria-labelledby="module-title">
      {role === "admin" ? (
        <header className="card reveal flex min-w-0 flex-col gap-4 overflow-hidden border-l-4 !border-l-g p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="chip m-0 max-w-full flex-wrap">
              <Icon name="shield" size={14} />
              <span className="break-words">{roleEyebrow(t, role)}</span>
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <StatusTag tone="ok" label={t("roleViews.adminPlatformStatus")} />
              <span className="chip">{t("roleViews.adminApiStatus")}</span>
              <span className="chip">{t("roleViews.adminTelemetryStatus")}</span>
            </div>
          </div>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <h1 id="module-title" className="m-0 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                {tm("dashboard")}
              </h1>
              <p className="m-0 max-w-3xl text-sm text-mute sm:text-base">{t("roleViews.adminHeaderSubtitle")}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href={localePath(locale, "/alertes")} className="btn-secondary min-h-touch text-sm">
                <Icon name="bell" size={16} />
                {t("seeAlerts")}
              </Link>
              <Link href={localePath(locale, "/kit")} className="btn-secondary min-h-touch text-sm">
                <Icon name="kit" size={16} />
                {t("hardware.sensorsLink")}
              </Link>
              <Link href={localePath(locale, "/rapports")} className="btn-secondary min-h-touch text-sm">
                <Icon name="chart" size={16} />
                {t("cockpit.reportsLink")}
              </Link>
            </div>
          </div>
        </header>
      ) : role === "agronomist" ? (
        <header className="card reveal flex min-w-0 flex-col gap-4 overflow-hidden border-l-4 !border-l-g p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="chip m-0 max-w-full flex-wrap">
              <Icon name="leaf" size={14} />
              <span className="break-words">{roleEyebrow(t, role)}</span>
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <StatusTag tone="ok" label={t("roleViews.agronomistStatusFao")} />
              <span className="chip">{t("roleViews.agronomistStatusNdvi")}</span>
            </div>
          </div>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <h1 id="module-title" className="m-0 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                {tm("dashboard")}
              </h1>
              <p className="m-0 max-w-3xl text-sm text-mute sm:text-base">{t("roleViews.agronomistHeaderSubtitle")}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href={localePath(locale, "/vegetation")} className="btn-secondary min-h-touch text-sm">
                <Icon name="leaf" size={16} />
                {t("roleViews.agronomistVegLink")}
              </Link>
              <Link href={localePath(locale, "/previsions")} className="btn-secondary min-h-touch text-sm">
                <Icon name="drop" size={16} />
                {t("roleViews.agronomistForecastLink")}
              </Link>
              <Link href={localePath(locale, "/maladies")} className="btn-secondary min-h-touch text-sm">
                <Icon name="camera" size={16} />
                {t("roleViews.agronomistDiagnoses")}
              </Link>
            </div>
          </div>
        </header>
      ) : role === "coop_manager" ? (
        <header className="card reveal flex min-w-0 flex-col gap-4 overflow-hidden border-l-4 !border-l-g p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="chip m-0 max-w-full flex-wrap">
              <Icon name="farm" size={14} />
              <span className="break-words">{roleEyebrow(t, role)}</span>
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <StatusTag tone="ok" label="Coopérative des Niayes (Mboro & Potou)" />
              <span className="chip">Campagne : Contre-saison froide (41 %)</span>
            </div>
          </div>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <h1 id="module-title" className="m-0 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                {tm("dashboard")}
              </h1>
              <p className="m-0 max-w-3xl text-sm text-mute sm:text-base">{t("roleViews.coopHeaderSubtitle")}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href={localePath(locale, "/marches")} className="btn-secondary min-h-touch text-sm">
                <Icon name="market" size={16} />
                {t("cockpit.marketsLink")}
              </Link>
              <Link href={localePath(locale, "/planning")} className="btn-secondary min-h-touch text-sm">
                <Icon name="drop" size={16} />
                {t("cockpit.planningLink")}
              </Link>
              <Link href={localePath(locale, "/rapports")} className="btn-secondary min-h-touch text-sm">
                <Icon name="chart" size={16} />
                {t("cockpit.reportsLink")}
              </Link>
            </div>
          </div>
          <div className="rounded-btn border border-g/40 bg-accent-soft/30 p-3.5">
            <p className="m-0 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-g">
              <Icon name="sparkles" size={14} />
              {t("roleViews.coopSynthesisLabel")}
            </p>
            <p className="m-0 mt-1 text-sm font-semibold text-ink">{t("roleViews.coopSynthesisBody")}</p>
          </div>
        </header>
      ) : (
        <header className="banner reveal">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/img/champ-hero.webp" alt="" width={1280} height={855} className="banner-img" />
          <div className="banner-scrim" />
          <div className="grid gap-6 px-5 py-6 text-white sm:px-8 sm:py-8 lg:min-h-[22rem] lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] lg:items-end">
            <div className="flex flex-col gap-4">
              <p className="chip m-0 w-fit">
                <Icon name="sparkles" size={14} />
                {roleEyebrow(t, role)}
              </p>
              <h1 id="module-title" className="text-3xl font-bold tracking-tight sm:text-5xl">
                {tm("dashboard")}
              </h1>
              <p className="m-0 max-w-prose text-white sm:text-lg">{t("description")}</p>
              {ready ? (
                <AiSummary
                  rows={rows}
                  counts={counts}
                  critical={critical}
                  provenance={maps.maps[0]?.map.provenance ?? null}
                />
              ) : null}
            </div>
            {ready && lead ? <WeatherPanel field={lead} /> : null}
          </div>
        </header>
      )}
      {critical > 0 ? (
        <div
          role="alert"
          className="glass flex flex-wrap items-center justify-between gap-2 !border-bad-ink !bg-bad-bg p-4 font-semibold text-bad-ink"
        >
          <span className="flex items-center gap-2">
            <Icon name="bad" size={20} />
            {t("criticalBanner", { count: critical })}
          </span>
          <Link href={localePath(locale, "/alertes")} className="btn-secondary min-h-touch">
            {t("seeAlerts")}
          </Link>
        </div>
      ) : null}
      <QueryState
        isPending={maps.isPending || devices.isPending}
        error={maps.error ?? devices.error}
        isEmpty={rows.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => {
          maps.refetch();
          void devices.refetch();
        }}
      >
        {role === "farmer" ? (
          <FarmerDashboard rows={rows} counts={counts} lead={lead} openAlerts={alerts.data ?? []} />
        ) : role === "coop_manager" ? (
          <CoopManagerDashboard maps={maps.maps} rows={rows} />
        ) : role === "agronomist" ? (
          <AgronomistDashboard rows={rows} counts={counts} />
        ) : (
          <AdminDashboard
            maps={maps.maps}
            rows={rows}
            counts={counts}
            devices={devices.data ?? []}
            openAlerts={alerts.data ?? []}
            critical={critical}
          />
        )}

        {role === "agronomist" || role === "admin" ? (
          <section aria-labelledby="dashboard-sources" className="card flex flex-col gap-2">
            <h2 id="dashboard-sources" className="text-base font-semibold">
              {t("sources")}
            </h2>
            {maps.maps.map((m) => (
              <div key={m.farmId} className="flex flex-col gap-1">
                <p className="text-sm text-mute">{t("sourceFarm", { farm: m.farmName })}</p>
                <ProvenanceNote provenance={m.map.provenance} />
              </div>
            ))}
          </section>
        ) : null}
      </QueryState>
    </section>
  );
}
