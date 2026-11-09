"use client";

import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId } from "react";

import type { Farm, Field } from "@/lib/types";

/**
 * Choix de la parcelle (regroupée par exploitation). La sélection est reportée dans l'URL
 * (?parcelle=…) pour qu'un lien partagé ouvre la même vue.
 */
export function FieldPicker({
  farms,
  fields,
  value,
  onChange,
}: {
  farms: readonly Farm[];
  fields: readonly Field[];
  value: string | null;
  onChange: (fieldId: string) => void;
}) {
  const t = useTranslations("common");
  const id = useId();
  const router = useRouter();
  const pathname = usePathname();
  const known = value !== null && fields.some((f) => f.id === value);

  // Parcelle absente ou inconnue : on prend la première, sans ajouter d'entrée d'historique.
  useEffect(() => {
    const first = fields[0];
    if (!known && first) onChange(first.id);
  }, [known, fields, onChange]);

  const select = (fieldId: string) => {
    onChange(fieldId);
    router.replace(`${pathname}?parcelle=${encodeURIComponent(fieldId)}`, { scroll: false });
  };

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {t("fieldPicker")}
      </label>
      <select
        id={id}
        className="field-input min-h-touch"
        value={known ? (value ?? "") : ""}
        onChange={(e) => select(e.target.value)}
      >
        {farms.map((farm) => {
          const own = fields.filter((f) => f.farm_id === farm.id);
          if (own.length === 0) return null;
          return (
            <optgroup key={farm.id} label={farm.name}>
              {own.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </optgroup>
          );
        })}
      </select>
    </div>
  );
}
