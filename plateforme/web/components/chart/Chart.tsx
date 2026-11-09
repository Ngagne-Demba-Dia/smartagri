"use client";

import { useTranslations } from "next-intl";
import { useId, useState, useSyncExternalStore, type KeyboardEvent } from "react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  BAND_OPACITY,
  BAR_MAX_WIDTH,
  DOT_RADIUS,
  LINE_WIDTH,
  chartTableHeaders,
  chartTableRows,
  describePoint,
  legendVisible,
  nextPointer,
  seriesColor,
  showDots,
  toChartRows,
  yDomain,
  type ChartSpec,
  type ValueFormatter,
} from "@/lib/chart-option";

/** La hauteur vient de .chart-box (app/globals.css). */
const CHART_HEIGHT = "100%";
const noopSubscribe = () => () => {};

function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (callback) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", callback);
      return () => list.removeEventListener("change", callback);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Rendu côté client seulement : la CSP refuse les attributs style du HTML servi (Recharts en pose). */
function useMounted(): boolean {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
}

interface TooltipEntry {
  dataKey?: unknown;
  name?: unknown;
  value?: unknown;
  color?: string;
}

function TooltipBox({
  active,
  payload,
  label,
  formatValue,
}: {
  active?: boolean;
  payload?: ReadonlyArray<TooltipEntry>;
  label?: unknown;
  formatValue: ValueFormatter;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="glass glass-strong !rounded-btn px-3 py-2 text-sm text-ink">
      <p className="font-semibold">{String(label ?? "")}</p>
      <ul>
        {payload.map((entry) => {
          const value = entry.value;
          const text = Array.isArray(value)
            ? `${formatValue(value[0] ?? null)} – ${formatValue(value[1] ?? null)}`
            : formatValue(typeof value === "number" ? value : null);
          return (
            <li key={String(entry.dataKey)} className="flex items-center gap-2">
              <svg width="10" height="10" aria-hidden="true">
                <rect width="10" height="10" rx="2" fill={entry.color ?? "currentColor"} />
              </svg>
              <span className="text-mute">{String(entry.name ?? "")}</span>
              <span className="ml-auto tabular-nums">{text}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Plot({
  spec,
  formatValue,
  pointer,
}: {
  spec: ChartSpec;
  formatValue: ValueFormatter;
  pointer: number;
}) {
  const reducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const rows = toChartRows(spec);
  const dots = showDots(spec);
  const animate = !reducedMotion;
  const focused = pointer >= 0 ? spec.categories[pointer] : undefined;
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <ComposedChart
        data={rows}
        margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
        accessibilityLayer={false}
      >
        <CartesianGrid vertical={false} stroke="var(--line)" />
        <XAxis
          dataKey="category"
          tickLine={false}
          axisLine={{ stroke: "var(--line)" }}
          tick={{ fill: "var(--mute)", fontSize: 12 }}
          minTickGap={16}
        />
        <YAxis
          width={44}
          domain={yDomain(spec)}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--mute)", fontSize: 12 }}
        />
        <Tooltip
          cursor={{ stroke: "var(--line)" }}
          content={(props) => <TooltipBox {...props} formatValue={formatValue} />}
        />
        {legendVisible(spec) ? (
          <Legend
            verticalAlign="top"
            height={28}
            formatter={(value) => <span className="text-ink">{String(value)}</span>}
          />
        ) : null}
        {spec.band ? (
          <Area
            dataKey={spec.band.id}
            name={spec.band.name}
            stroke="none"
            fill={seriesColor(0)}
            fillOpacity={BAND_OPACITY}
            isAnimationActive={animate}
            connectNulls={false}
          />
        ) : null}
        {spec.series.map((s, index) => {
          const color = seriesColor(index);
          if (s.kind === "bar") {
            return (
              <Bar
                key={s.id}
                dataKey={s.id}
                name={s.name}
                fill={color}
                maxBarSize={BAR_MAX_WIDTH}
                radius={[4, 4, 0, 0]}
                isAnimationActive={animate}
              />
            );
          }
          return (
            <Line
              key={s.id}
              type="monotone"
              dataKey={s.id}
              name={s.name}
              stroke={color}
              strokeWidth={LINE_WIDTH}
              connectNulls={false}
              dot={dots ? { r: DOT_RADIUS, fill: color, stroke: "var(--card)", strokeWidth: 2 } : false}
              activeDot={{ r: DOT_RADIUS + 1, fill: color, stroke: "var(--card)", strokeWidth: 2 }}
              isAnimationActive={animate}
            />
          );
        })}
        {(spec.references ?? []).map((r) => (
          <ReferenceLine
            key={`${r.label}-${r.value}`}
            y={r.value}
            stroke="var(--mute)"
            strokeDasharray="6 4"
            strokeWidth={1.5}
            ifOverflow="extendDomain"
            label={{ value: r.label, position: "insideTopRight", fill: "var(--ink)", fontSize: 12 }}
          />
        ))}
        {focused !== undefined ? <ReferenceLine x={focused} stroke="var(--ink)" strokeWidth={1} /> : null}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/**
 * Graphique conforme à doc 10 §5 (règles visuelles dans lib/chart-option.ts).
 * Accessibilité : résumé lu par les lecteurs d'écran, flèches ←/→ pour parcourir les points
 * (valeur affichée et annoncée dans une zone live), Échap pour sortir, bouton « Voir en tableau ».
 */
export function Chart({
  title,
  spec,
  formatValue,
}: {
  title: string;
  spec: ChartSpec;
  formatValue: ValueFormatter;
}) {
  const t = useTranslations("chart");
  const mounted = useMounted();
  const [pointer, setPointer] = useState(-1);
  const [showTable, setShowTable] = useState(false);
  const tableId = useId();
  const hintId = useId();
  const readout =
    pointer >= 0 && pointer < spec.categories.length ? describePoint(spec, pointer, formatValue) : "";

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      setPointer(-1);
      return;
    }
    const next = nextPointer(pointer, event.key, spec.categories.length);
    if (next === null) return;
    event.preventDefault();
    setPointer(next);
  };

  return (
    <figure className="card flex flex-col gap-2">
      <figcaption className="font-semibold">{title}</figcaption>
      <p className="text-xs text-mute" aria-hidden="true">
        {spec.unit}
      </p>
      <div
        role="img"
        aria-label={spec.summary}
        aria-describedby={hintId}
        tabIndex={0}
        onKeyDown={onKeyDown}
        onBlur={() => setPointer(-1)}
        className="chart-box rounded-btn"
      >
        {mounted ? <Plot spec={spec} formatValue={formatValue} pointer={pointer} /> : null}
      </div>
      <p id={hintId} className="sr-only">
        {t("keyboardHint")}
      </p>
      <p aria-live="polite" className={readout ? "text-sm tabular-nums" : "sr-only"}>
        {readout}
      </p>
      <button
        type="button"
        className="btn-secondary self-start"
        aria-expanded={showTable}
        aria-controls={tableId}
        onClick={() => setShowTable((v) => !v)}
      >
        {showTable ? t("hideTable") : t("showTable")}
      </button>
      <div id={tableId} hidden={!showTable} className="relative overflow-x-auto">
        {showTable ? (
          <table className="w-full border-collapse text-left text-sm">
            <caption className="sr-only">{title}</caption>
            <thead>
              <tr className="border-b border-line text-mute">
                <th scope="col" className="px-2 py-1">
                  {t("category")}
                </th>
                {chartTableHeaders(spec, { low: t("bandLow"), high: t("bandHigh") }).map((header) => (
                  <th key={header} scope="col" className="px-2 py-1 text-right">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {chartTableRows(spec).map((row, index) => (
                <tr key={index} className="border-b border-line last:border-0">
                  <th scope="row" className="px-2 py-1 font-normal">
                    {row.category}
                  </th>
                  {row.values.map((v, i) => (
                    <td key={i} className="px-2 py-1 text-right tabular-nums">
                      {formatValue(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </div>
    </figure>
  );
}
