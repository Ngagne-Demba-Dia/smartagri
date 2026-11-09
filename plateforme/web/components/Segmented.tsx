"use client";

import { useId } from "react";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

/** Choix exclusif court (fenêtre de temps, horizon) : boutons radio natifs, flèches du clavier incluses. */
export function Segmented<T extends string>({
  legend,
  options,
  value,
  onChange,
}: {
  legend: string;
  options: readonly SegmentedOption<T>[];
  value: T;
  onChange: (next: T) => void;
}) {
  const name = useId();
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="mb-1 p-0 text-sm text-mute">{legend}</legend>
      <div className="inline-flex max-w-full flex-wrap gap-1 rounded-full border border-glass-edge bg-surface p-1 backdrop-blur-md">
        {options.map((option) => (
          <label
            key={option.value}
            className="relative flex min-h-touch min-w-touch cursor-pointer items-center justify-center rounded-btn px-3 text-sm font-semibold text-ink has-[:checked]:bg-g has-[:checked]:text-on-g has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-[var(--focus)]"
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
