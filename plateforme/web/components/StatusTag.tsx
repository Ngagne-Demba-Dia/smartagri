import type { Tone } from "@/lib/status";

import { Icon, type IconName } from "./Icon";

const TONE_CLASS: Record<Tone, string> = {
  ok: "bg-ok-bg text-ok-ink",
  warn: "bg-warn-bg text-warn-ink",
  bad: "bg-bad-bg text-bad-ink",
  info: "bg-card text-ink border border-glass-edge",
};

const TONE_ICON: Record<Tone, IconName> = { ok: "check", warn: "warn", bad: "bad", info: "info" };

/** État = couleur + icône + mot (doc 10 §5) : jamais la couleur seule. */
export function StatusTag({ tone, label }: { tone: Tone; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-semibold shadow-[inset_0_1px_0_var(--glass-rim),0_1px_2px_rgb(0_0_0/0.12)] ${TONE_CLASS[tone]}`}
    >
      <Icon name={TONE_ICON[tone]} size={16} />
      {label}
    </span>
  );
}
