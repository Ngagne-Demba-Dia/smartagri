"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { DevicePicker } from "@/features/kit/DevicePicker";
import { KitHealth } from "@/features/kit/KitHealth";
import { QueryState } from "@/components/QueryState";
import { useDevices } from "@/hooks/devices";

/** Santé d'un kit au choix (service 13, doc 18 §10), pour l'écran Équipements. */
export function KitHealthSection() {
  const t = useTranslations("kit");
  const devices = useDevices();
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const list = devices.data ?? [];
  const device = list.find((d) => d.id === deviceId) ?? null;
  return (
    <QueryState
      isPending={devices.isPending}
      error={devices.error}
      isEmpty={list.length === 0}
      emptyLabel={t("noDevices")}
      onRetry={() => void devices.refetch()}
    >
      <DevicePicker devices={list} value={deviceId} onChange={setDeviceId} />
      {device ? <KitHealth deviceId={device.id} /> : null}
    </QueryState>
  );
}
