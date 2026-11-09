import { Icon } from "./Icon";

export type StepState = "done" | "current" | "todo";

export interface StepItem {
  key: string;
  label: string;
  state: StepState;
  /** Complément (date) affiché sous le libellé. */
  detail?: string;
}

const BADGE_CLASS: Record<StepState, string> = {
  done: "bg-g text-on-g",
  current: "bg-ok-bg text-ok-ink",
  todo: "bg-surface",
};

/** Étapes d'un cycle (semis → récolte) : l'état se lit par l'icône et le mot, pas seulement par la couleur. */
export function Steps({
  items,
  label,
  stateLabels,
}: {
  items: readonly StepItem[];
  label: string;
  stateLabels: Record<StepState, string>;
}) {
  return (
    <ol aria-label={label} className="m-0 flex list-none flex-wrap gap-x-4 gap-y-2 p-0">
      {items.map((item) => (
        <li
          key={item.key}
          aria-current={item.state === "current" ? "step" : undefined}
          className={`flex min-w-0 items-start gap-2 ${item.state === "todo" ? "text-mute" : "text-ink"}`}
        >
          <span
            className={`mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full ${BADGE_CLASS[item.state]}`}
          >
            <Icon name={item.state === "done" ? "check" : "sprout"} size={14} />
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="break-words font-semibold">{item.label}</span>
            <span className="text-xs text-mute">
              {stateLabels[item.state]}
              {item.detail ? ` · ${item.detail}` : ""}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}
