"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import type { Farm } from "@/lib/types";

/** Choix de l'exploitation. Sans effet de bord : la valeur affichée est déduite par le parent. */
export function FarmPicker({
  farms,
  value,
  onChange,
}: {
  farms: readonly Farm[];
  value: string | null;
  onChange: (farmId: string) => void;
}) {
  const t = useTranslations("common");
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {t("farmPicker")}
      </label>
      <select
        id={id}
        className="field-input min-h-touch"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        {farms.map((farm) => (
          <option key={farm.id} value={farm.id}>
            {farm.name}
          </option>
        ))}
      </select>
    </div>
  );
}
