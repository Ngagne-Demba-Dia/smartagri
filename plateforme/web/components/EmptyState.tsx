import type { ReactNode } from "react";

/** Illustration neutre (pousse dans un sillon) : décorative, la phrase porte le sens. */
function EmptyArt() {
  return (
    <svg width="96" height="72" viewBox="0 0 96 72" fill="none" aria-hidden="true" focusable="false">
      <ellipse cx="48" cy="62" rx="40" ry="7" className="fill-line" />
      <path d="M48 58V32" className="stroke-g" strokeWidth="3" strokeLinecap="round" />
      <path d="M48 40c-12 0-18-7-18-17 11 0 18 6 18 17z" className="fill-g2" />
      <path d="M48 34c0-10 6-16 17-16 0 10-6 16-17 16z" className="fill-g" />
    </svg>
  );
}

/** État vide : un titre court, une explication facultative et une action facultative. */
export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center gap-3 py-8 text-center">
      <EmptyArt />
      <p className="font-semibold">{title}</p>
      {hint ? <p className="max-w-prose text-mute">{hint}</p> : null}
      {action}
    </div>
  );
}
