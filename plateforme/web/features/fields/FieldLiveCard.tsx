"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";

import { Icon } from "@/components/Icon";
import { CropArt, Furrows } from "@/components/Illustrations";
import { Meter } from "@/components/Meter";
import { StatusTag } from "@/components/StatusTag";
import type { Locale } from "@/i18n/routing";
import { formatNumber, formatPct } from "@/lib/format";
import { waterQualityForField } from "@/lib/irrigation";
import { localePath } from "@/lib/nav";
import type { FieldOverview } from "@/lib/overview";
import type { MoistureVerdict, Tone } from "@/lib/status";
import { VERDICT_TONE } from "@/lib/status";
import { useIrrigationNeed } from "@/services/ai/irrigation-need";

/**
 * Une seule photo existe : chaque parcelle en montre un autre cadrage (choisi par son identifiant), pour que
 * la grille ne répète pas la même vignette. Classes écrites en entier : Tailwind ne garde que celles qu'il lit.
 */
const CROPS = [
  "object-[12%_88%] origin-[12%_88%] scale-[1.5]",
  "object-[48%_92%] origin-[48%_92%] scale-[1.6]",
  "object-[82%_80%] origin-[82%_80%] scale-[1.45]",
  "object-[30%_55%] origin-[30%_55%] scale-[1.25]",
  "object-[70%_45%] origin-[70%_45%] scale-[1.3]",
  "object-[55%_30%] origin-[55%_30%] scale-[1.15]",
] as const;

function cropFor(fieldId: string): string {
  let hash = 0;
  for (const char of fieldId) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return CROPS[hash % CROPS.length] ?? CROPS[0];
}

const RING_RADIUS = 26;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;
const RING_BOX = 64;
const RING_CENTER = RING_BOX / 2;
const PERCENT = 100;

/** Liseré de couleur au pied de la photo : le verdict se voit avant de se lire. */
const VERDICT_EDGE: Record<MoistureVerdict, string> = {
  dry: "bg-bad-ink",
  ok: "bg-accent",
  wet: "bg-blue",
  unknown: "bg-mute",
};

const RING_TONE: Record<MoistureVerdict, string> = {
  dry: "text-bad-ink",
  ok: "text-accent",
  wet: "text-blue",
  unknown: "text-mute",
};

/** Anneau d'humidité en SVG (la CSP interdit style= : la longueur d'arc passe par un attribut). */
function MoistureRing({ moisture, verdict }: { moisture: number | null; verdict: MoistureVerdict }) {
  const filled = moisture === null ? 0 : (Math.min(PERCENT, Math.max(0, moisture)) / PERCENT) * RING_CIRCUMFERENCE;
  return (
    <div className="relative h-16 w-16 shrink-0">
      <svg viewBox={`0 0 ${RING_BOX} ${RING_BOX}`} className={`ring-anim h-16 w-16 ${RING_TONE[verdict]}`} aria-hidden="true">
        <circle
          cx={RING_CENTER}
          cy={RING_CENTER}
          r={RING_RADIUS}
          fill="none"
          strokeWidth={7}
          className="stroke-ink-soft"
        />
        <circle
          cx={RING_CENTER}
          cy={RING_CENTER}
          r={RING_RADIUS}
          fill="none"
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${RING_CIRCUMFERENCE}`}
          transform={`rotate(-90 ${RING_CENTER} ${RING_CENTER})`}
          className="stroke-current"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold tabular-nums text-ink">
        {formatPct(moisture)}
      </span>
    </div>
  );
}

/** Carte « vivante » d'une parcelle (allégée P0) : verdict explicite, 1 phrase d'action, 3 mesures clés, 1 bouton principal. */
export function FieldLiveCard({ row }: { row: FieldOverview }) {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const need = useIrrigationNeed(row.fieldId);
  const wq = waterQualityForField(row.fieldId);
  const detail = localePath(locale, `/parcelles/${encodeURIComponent(row.fieldId)}`);

  const badgeTone: Tone =
    row.deviceId === null
      ? "info"
      : row.freshness === "silent"
        ? "warn"
        : VERDICT_TONE[row.verdict];

  const badgeLabel =
    row.deviceId === null
      ? t("verdict.noKit")
      : row.freshness === "silent"
        ? t("freshness.silent")
        : t(`verdict.${row.verdict}`);

  const actionSentence =
    row.deviceId === null
      ? t("cardAction.noKit")
      : row.freshness === "silent"
        ? t("cardAction.silent")
        : need.data?.defer
          ? t("cardAction.deferred", { mm: formatNumber(need.data.rain_expected_mm, 1) })
          : need.data && need.data.need_mm > 0
            ? t("cardAction.irrigate", {
                mm: formatNumber(need.data.need_mm, 1),
                m3: formatNumber(need.data.volume_m3, 1),
              })
            : t("cardAction.ok");

  return (
    <li className="card card-link group flex h-full flex-col justify-between overflow-hidden !p-0 sm:!p-0">
      <div className="relative isolate h-40 overflow-hidden">
        <div className="absolute inset-0 -z-20 transition-transform duration-[900ms] ease-out group-hover:scale-110">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/img/champ-hero.webp"
            alt=""
            width={1280}
            height={855}
            loading="lazy"
            className={`h-full w-full object-cover saturate-[1.25] contrast-[1.05] ${cropFor(row.fieldId)}`}
          />
        </div>
        <div className="absolute inset-0 -z-10 bg-gradient-to-t from-black/75 via-black/15 to-white/5" />
        <Furrows className="absolute inset-x-0 bottom-0 -z-10 h-16 w-full text-white" />
        <div className="flex h-full flex-col justify-between p-3 text-white">
          <div className="flex items-start justify-between gap-2">
            <span
              className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/60 bg-white/75 shadow-pop backdrop-blur-sm transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-105"
              aria-hidden="true"
            >
              <CropArt crop={row.crop} size={38} />
            </span>
            <StatusTag tone={badgeTone} label={badgeLabel} />
          </div>
          <div>
            <h2 className="text-xl font-bold leading-tight text-white drop-shadow-[0_2px_8px_rgb(0_0_0/0.5)]">
              {row.name}
            </h2>
            <p className="text-sm font-medium text-white drop-shadow-[0_1px_6px_rgb(0_0_0/0.6)]">
              {row.crop ?? t("noCrop")}
              {row.areaHa !== null ? ` · ${formatNumber(row.areaHa, 2)} ha` : ""}
            </p>
          </div>
        </div>
        <span className={`absolute inset-x-0 bottom-0 h-1 ${VERDICT_EDGE[row.verdict]}`} aria-hidden="true" />
      </div>

      <div className="flex flex-1 flex-col justify-between gap-3 p-4">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <MoistureRing moisture={row.moisture} verdict={row.verdict} />
            <div className="min-w-0 flex-1">
              <p className="m-0 text-sm font-semibold text-ink">{t("moisture")}</p>
              {row.moisture !== null ? (
                <Meter
                  value={row.moisture}
                  label={t("moistureMeter", { field: row.name })}
                  valueText={formatPct(row.moisture)}
                  marks={
                    row.thresholds
                      ? [
                          {
                            value: row.thresholds.start_pct,
                            label: t("markStart", { value: row.thresholds.start_pct }),
                          },
                          {
                            value: row.thresholds.stop_pct,
                            label: t("markStop", { value: row.thresholds.stop_pct }),
                          },
                        ]
                      : []
                  }
                />
              ) : (
                <p className="m-0 text-sm text-mute">{t("verdict.noKit")}</p>
              )}
            </div>
          </div>

          <p className="m-0 rounded-btn bg-surface px-3 py-2 text-sm font-medium text-ink">{actionSentence}</p>

          <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
            <li className="chip">
              <Icon name="drop" size={14} />
              <span className="font-semibold tabular-nums">
                {need.data
                  ? need.data.defer
                    ? t("telemetry.needDeferred")
                    : t("telemetry.need24h", {
                        mm: formatNumber(need.data.need_mm, 1),
                        m3: formatNumber(need.data.volume_m3, 1),
                      })
                  : t("noKit")}
              </span>
            </li>
            <li className="chip">
              <Icon name="kit" size={14} />
              <span className="tabular-nums">{t("telemetry.ph", { ph: formatNumber(wq.ph, 1) })}</span>
            </li>
            {row.openAlerts > 0 ? (
              <li className="chip !border-bad-ink font-semibold !text-bad-ink">
                <Icon name="bell" size={14} />
                {t("openAlerts", { count: row.openAlerts })}
              </li>
            ) : (
              <li className="chip">
                <Icon name="check" size={14} />
                <span>{row.deviceSerial ? `${row.deviceSerial} · ${t(`freshness.${row.freshness ?? "fresh"}`)}` : t("noKit")}</span>
              </li>
            )}
          </ul>
        </div>

        <div className="pt-1">
          <Link href={detail} className="btn-secondary min-h-touch w-full justify-center">
            {t("details")}
          </Link>
        </div>
      </div>
    </li>
  );
}

