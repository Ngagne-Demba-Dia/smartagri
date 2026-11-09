"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { DevicePicker } from "@/features/kit/DevicePicker";
import { KitHealth } from "@/features/kit/KitHealth";
import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { useDevices } from "@/hooks/devices";
import type { Locale } from "@/i18n/routing";
import type { KitParameters, ParameterBlock } from "@/lib/contracts/device";
import { formatDate, formatDateTime, formatNumber } from "@/lib/format";
import { blockStatus, isNotPublished, validityDays } from "@/lib/kit";
import { localePath } from "@/lib/nav";
import type { Device } from "@/lib/types";
import { useKitParameters } from "@/services/ai/kit-parameters";

const EMPTY = "—";
const KC_DIGITS = 2;

function Block({
  params,
  block,
  title,
  children,
}: {
  params: KitParameters;
  block: ParameterBlock;
  title: string;
  children: ReactNode;
}) {
  const t = useTranslations("kit");
  const status = blockStatus(params, block);
  return (
    <section className="card flex flex-col gap-2" aria-label={title}>
      <h2 className="font-semibold">{title}</h2>
      {status === "expired" ? (
        <StatusTag tone="warn" label={t("expired", { days: validityDays(block) })} />
      ) : null}
      {children}
      <ProvenanceNote provenance={params.provenance[block]} />
    </section>
  );
}

function SeuilsBlock({ params, device }: { params: KitParameters; device: Device }) {
  const t = useTranslations("kit");
  const locale = useLocale() as Locale;
  const current = device.thresholds?.desired ?? null;
  return (
    <Block params={params} block="seuils" title={t("seuilsTitle")}>
      <p className="text-lg font-bold">
        {t(params.applied ? "seuilsApplied" : "seuilsAdvised", {
          start: params.seuils.start,
          stop: params.seuils.stop,
        })}
      </p>
      <p className="text-sm">
        {current
          ? t("seuilsCurrent", {
              start: current.start_pct,
              stop: current.stop_pct,
            })
          : t("seuilsNoCurrent")}
      </p>
      {device.field_id ? (
        <Link
          className="btn btn-secondary self-start"
          href={localePath(locale, `/parcelles/${device.field_id}`)}
        >
          {t("seuilsLink")}
        </Link>
      ) : null}
      <p className="text-xs text-mute">{t("seuilsNote")}</p>
    </Block>
  );
}

function ParametersCards({ params, device }: { params: KitParameters; device: Device }) {
  const t = useTranslations("kit");
  const { npk, etalonnage, agro } = params;
  return (
    <div className="flex flex-col gap-4">
      <p role="status" className="text-sm">
        {t("generation", {
          version: params.version,
          date: formatDateTime(params.emis_a),
        })}
      </p>
      <SeuilsBlock params={params} device={device} />
      <Block params={params} block="npk" title={t("npkTitle")}>
        <ul className="text-sm">
          <li>{t("npkN", { value: formatNumber(npk.n, 1) })}</li>
          <li>{t("npkP", { value: formatNumber(npk.p, 1) })}</li>
          <li>{t("npkK", { value: formatNumber(npk.k, 1) })}</li>
        </ul>
        <p className="text-xs text-mute">{t("npkNote")}</p>
      </Block>
      <Block params={params} block="etalonnage" title={t("etalTitle")}>
        <ul className="text-sm">
          <li>{t("etalDry", { value: etalonnage.adc_sec })}</li>
          <li>{t("etalWater", { value: etalonnage.adc_eau })}</li>
        </ul>
      </Block>
      <Block params={params} block="agro" title={t("agroTitle")}>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 text-sm">
          <dt className="text-mute">{t("culture")}</dt>
          <dd>{agro.culture ?? EMPTY}</dd>
          <dt className="text-mute">{t("stage")}</dt>
          <dd>{agro.stade ?? EMPTY}</dd>
          <dt className="text-mute">{t("sowing")}</dt>
          <dd>{agro.date_semis ? formatDate(agro.date_semis) : EMPTY}</dd>
          <dt className="text-mute">{t("kc")}</dt>
          <dd>{agro.kc === null ? EMPTY : formatNumber(agro.kc, KC_DIGITS)}</dd>
        </dl>
      </Block>
    </div>
  );
}

function DeviceParameters({ device }: { device: Device }) {
  const t = useTranslations("kit");
  const query = useKitParameters(device.id);
  const notPublished = isNotPublished(query.error);
  return (
    <QueryState
      isPending={query.isPending}
      error={notPublished ? null : query.error}
      isEmpty={notPublished || !query.data}
      emptyLabel={t("empty")}
      onRetry={() => void query.refetch()}
    >
      {query.data ? <ParametersCards params={query.data} device={device} /> : null}
    </QueryState>
  );
}

/** Kit (service 7, doc 18 §4) : jeu de paramètres conseillé, bloc par bloc, avec sa provenance. Rien n'est appliqué ici. */
export function KitView({ initialDeviceId }: { initialDeviceId: string | null }) {
  const t = useTranslations("kit");
  const tm = useTranslations("modules");
  const devices = useDevices();
  const [deviceId, setDeviceId] = useState<string | null>(initialDeviceId);
  const list = devices.data ?? [];
  const device = list.find((d) => d.id === deviceId) ?? null;

  return (
    <ModuleShell title={tm("kit")} description={t("description")}>
      <QueryState
        isPending={devices.isPending}
        error={devices.error}
        isEmpty={list.length === 0}
        emptyLabel={t("noDevices")}
        onRetry={() => void devices.refetch()}
      >
        <DevicePicker devices={list} value={deviceId} onChange={setDeviceId} />
        {device ? <KitHealth deviceId={device.id} /> : null}
        {device ? <DeviceParameters device={device} /> : null}
      </QueryState>
    </ModuleShell>
  );
}
