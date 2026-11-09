import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";

/**
 * Tuile d'indicateur : libellé, valeur lue en premier (le verdict avant les chiffres), unité et complément.
 * Une liste de tuiles se met dans un <dl> : la tuile rend un <div> contenant dt/dd.
 */
export function KpiCard({
  label,
  value,
  unit,
  icon,
  hint,
  children,
}: {
  label: string;
  value: string;
  unit?: string;
  icon?: IconName;
  hint?: string;
  children?: ReactNode;
}) {
  return (
    <div className="card card-link group flex min-w-0 flex-col gap-1.5">
      <dt className="flex items-center gap-2 text-sm text-mute">
        {icon ? (
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-g">
            <Icon name={icon} size={18} />
          </span>
        ) : null}
        <span className="break-words">{label}</span>
      </dt>
      <dd className="m-0 flex flex-col gap-1">
        <span className="break-words text-3xl font-bold tracking-tight text-ink tabular-nums">
          {value}
          {unit ? <span className="ml-1 text-base font-semibold text-mute">{unit}</span> : null}
        </span>
        {hint ? <span className="text-xs text-mute">{hint}</span> : null}
        {children}
      </dd>
    </div>
  );
}
