"use client";

import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId } from "react";

import type { Device } from "@/lib/types";

/** Choix du kit ; la sélection est reportée dans l'URL (?kit=…) pour qu'un lien partagé ouvre le même kit. */
export function DevicePicker({
  devices,
  value,
  onChange,
}: {
  devices: readonly Device[];
  value: string | null;
  onChange: (id: string) => void;
}) {
  const t = useTranslations("kit");
  const id = useId();
  const router = useRouter();
  const pathname = usePathname();
  const known = value !== null && devices.some((d) => d.id === value);

  // Kit absent ou inconnu : on prend le premier, sans ajouter d'entrée d'historique.
  useEffect(() => {
    const first = devices[0];
    if (!known && first) onChange(first.id);
  }, [known, devices, onChange]);

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {t("deviceLabel")}
      </label>
      <select
        id={id}
        className="field-input min-h-touch"
        value={known ? (value ?? "") : ""}
        onChange={(e) => {
          onChange(e.target.value);
          router.replace(`${pathname}?kit=${encodeURIComponent(e.target.value)}`, { scroll: false });
        }}
      >
        {devices.map((d) => (
          <option key={d.id} value={d.id}>
            {t("deviceOption", { name: d.name ?? d.serial, serial: d.serial })}
          </option>
        ))}
      </select>
    </div>
  );
}
