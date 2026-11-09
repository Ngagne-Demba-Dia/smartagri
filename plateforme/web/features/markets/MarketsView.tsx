"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { AiCard } from "@/components/AiCard";
import { Chart } from "@/components/chart/Chart";
import { DataTable, type Column } from "@/components/DataTable";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { Segmented } from "@/components/Segmented";
import type { ChartSpec, ValueFormatter } from "@/lib/chart-option";
import type { PriceForecast } from "@/lib/contracts/org";
import { formatDate, formatNumber } from "@/lib/format";
import {
  changePct,
  cropKey,
  PRICE_CROPS,
  PRICE_MARKETS,
  sortedPriceHorizons,
  type PriceCrop,
  type PriceHorizon,
  type PriceMarket,
} from "@/lib/prices";
import { usePriceForecast } from "@/services/ai/price-forecast";

const UNIT = "FCFA/kg";

const formatPrice: ValueFormatter = (v) => (v === null ? formatNumber(v) : `${formatNumber(v)} ${UNIT}`);

function usePriceChart(data: PriceForecast, cropLabel: string): ChartSpec | null {
  const t = useTranslations("markets");
  return useMemo(() => {
    const horizons = sortedPriceHorizons(data.horizons);
    if (horizons.length === 0) return null;
    const observed = data.observed?.price ?? null;
    const lows = horizons.map((h) => h.p10);
    const highs = horizons.map((h) => h.p90);
    return {
      categories: [t("observedLabel"), ...horizons.map((h) => t("week", { weeks: h.weeks }))],
      series: [
        { id: "p50", name: t("median"), kind: "line", values: [observed, ...horizons.map((h) => h.p50)] },
      ],
      band: { id: "p10p90", name: t("band"), low: [null, ...lows], high: [null, ...highs] },
      unit: UNIT,
      yMin: 0,
      summary: t("chartSummary", {
        crop: cropLabel,
        count: horizons.length,
        low: formatPrice(Math.min(...lows)),
        high: formatPrice(Math.max(...highs)),
      }),
    } satisfies ChartSpec;
  }, [data, cropLabel, t]);
}

function Result({
  data,
  cropLabel,
  marketLabel,
}: {
  data: PriceForecast;
  cropLabel: string;
  marketLabel: string;
}) {
  const t = useTranslations("markets");
  const chart = usePriceChart(data, cropLabel);
  const observed = data.observed;
  const rows = sortedPriceHorizons(data.horizons);
  const columns: Column<PriceHorizon>[] = [
    { key: "week", header: t("colWeek"), cell: (h) => t("week", { weeks: h.weeks }) },
    { key: "p50", header: t("median"), numeric: true, cell: (h) => formatPrice(h.p50) },
    {
      key: "range",
      header: t("band"),
      numeric: true,
      cell: (h) => t("range", { low: formatNumber(h.p10), high: formatPrice(h.p90) }),
    },
    {
      key: "change",
      header: t("colChange"),
      numeric: true,
      cell: (h) => {
        const pct = changePct(observed?.price ?? null, h.p50);
        return pct === null ? formatNumber(null) : `${pct > 0 ? "+" : ""}${formatNumber(pct)} %`;
      },
    },
  ];
  return (
    <AiCard title={t("cardTitle", { crop: cropLabel, market: marketLabel })} provenance={data.provenance}>
      <div className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            label={t("observed")}
            value={observed ? formatNumber(observed.price) : formatNumber(null)}
            unit={observed ? UNIT : undefined}
            hint={observed ? t("observedOn", { date: formatDate(observed.date) }) : t("noObserved")}
          />
          {rows.slice(0, 3).map((h) => {
            const pct = changePct(observed?.price ?? null, h.p50);
            return (
              <KpiCard
                key={h.weeks}
                label={t("week", { weeks: h.weeks })}
                value={formatNumber(h.p50)}
                unit={UNIT}
                hint={t("range", { low: formatNumber(h.p10), high: formatPrice(h.p90) })}
              >
                {pct !== null ? (
                  <span className="text-xs text-mute">
                    {t("change", { value: `${pct > 0 ? "+" : ""}${formatNumber(pct)} %` })}
                  </span>
                ) : null}
              </KpiCard>
            );
          })}
        </dl>
        {chart ? <Chart title={t("chartTitle")} spec={chart} formatValue={formatPrice} /> : null}
        <DataTable
          caption={t("chartTitle")}
          captionHidden
          columns={columns}
          rows={rows}
          rowKey={(h) => String(h.weeks)}
        />
        <p className="text-sm text-mute">{t("caveat")}</p>
      </div>
    </AiCard>
  );
}

/** Prix du marché (service 15, doc 18) : prix de gros attendus à 1–4 semaines, plage p10–p90 du modèle. */
export function MarketsView() {
  const t = useTranslations("markets");
  const tm = useTranslations("modules");
  const [crop, setCrop] = useState<PriceCrop>(PRICE_CROPS[0]);
  const [market, setMarket] = useState<PriceMarket>(PRICE_MARKETS[0]);
  const query = usePriceForecast(crop, market);
  const cropLabel = t(`cropNames.${cropKey(crop)}`);
  const marketLabel = t(`marketNames.${market}`);

  return (
    <ModuleShell title={tm("markets")} description={t("description")} version="V3">
      <div className="flex flex-wrap items-end gap-4">
        <Segmented
          legend={t("cropLegend")}
          value={crop}
          onChange={setCrop}
          options={PRICE_CROPS.map((c) => ({ value: c, label: t(`cropNames.${cropKey(c)}`) }))}
        />
        <Segmented
          legend={t("marketLegend")}
          value={market}
          onChange={setMarket}
          options={PRICE_MARKETS.map((m) => ({ value: m, label: t(`marketNames.${m}`) }))}
        />
      </div>
      <QueryState
        isPending={query.isPending}
        error={query.error}
        isEmpty={!query.data || query.data.horizons.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => void query.refetch()}
      >
        {query.data ? <Result data={query.data} cropLabel={cropLabel} marketLabel={marketLabel} /> : null}
      </QueryState>
    </ModuleShell>
  );
}
