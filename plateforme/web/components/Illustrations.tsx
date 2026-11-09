/**
 * Illustrations agricoles en SVG vectoriel : décoratives (aria-hidden), sans image ni police externe, couleurs en
 * attributs (la CSP à nonce interdit style=). Les mouvements sont des classes de app/globals.css (transform/opacity).
 */

import { useId } from "react";

type CropKind = "onion" | "millet" | "maize" | "tomato" | "rice" | "groundnut" | "seedling";

const CROP_PATTERNS: ReadonlyArray<readonly [RegExp, CropKind]> = [
  [/oignon|onion|echalote|échalote/i, "onion"],
  [/\bmil\b|millet|sorgho|sorghum|petit mil/i, "millet"],
  [/ma[iï]s|corn|maize/i, "maize"],
  [/tomate|tomato|poivron|piment/i, "tomato"],
  [/\briz\b|rice|paddy/i, "rice"],
  [/arachide|groundnut|peanut|ni[ée]b[ée]|haricot|bean/i, "groundnut"],
];

export function cropKind(crop: string | null | undefined): CropKind {
  if (!crop) return "seedling";
  return CROP_PATTERNS.find(([pattern]) => pattern.test(crop))?.[1] ?? "seedling";
}

const STEM = "#2f8a3e";
const LEAF = "#58b25f";
const LEAF_DARK = "#1f6b2c";
const SOIL = "#7a5230";

function CropShape({ kind }: { kind: CropKind }) {
  switch (kind) {
    case "onion":
      return (
        <g>
          <path d="M32 40c-9-2-13 5-9 10s14 5 18 0 0-12-9-10z" fill="#e7a8b6" />
          <path d="M32 40c-4 1-6 6-5 11" stroke="#c9758b" strokeWidth="1.4" fill="none" strokeLinecap="round" />
          <path d="M32 40V14M32 38c-3-10-9-14-13-16M32 38c3-10 8-15 12-17" stroke={STEM} strokeWidth="3" fill="none" strokeLinecap="round" />
        </g>
      );
    case "millet":
      return (
        <g>
          <path d="M32 56V22" stroke={STEM} strokeWidth="3" strokeLinecap="round" />
          <ellipse cx="32" cy="14" rx="5.5" ry="12" fill="#d9a441" />
          <path d="M28 8l8 3M27.5 14l9 0M28 20l8-3" stroke="#a97817" strokeWidth="1.2" strokeLinecap="round" />
          <path d="M32 46c-8-1-12-7-13-12 8 0 12 5 13 12zM32 40c7-1 11-6 12-11-8 0-11 5-12 11z" fill={LEAF} />
        </g>
      );
    case "maize":
      return (
        <g>
          <path d="M32 58V20" stroke={STEM} strokeWidth="3.5" strokeLinecap="round" />
          <path d="M32 48c-10-1-16-8-17-15 10 0 16 6 17 15zM32 38c9-1 15-7 16-14-9 0-15 6-16 14z" fill={LEAF} />
          <path d="M32 34c-6-3-8-12-5-19 6 3 8 12 5 19z" fill="#f0c24b" />
          <path d="M32 34c-3-3-5-5-5-9M32 34c0-6 1-10 5-12" stroke="#a97817" strokeWidth="1" fill="none" />
        </g>
      );
    case "tomato":
      return (
        <g>
          <path d="M32 54V22" stroke={STEM} strokeWidth="3" strokeLinecap="round" />
          <circle cx="23" cy="38" r="8" fill="#e5483d" />
          <circle cx="41" cy="30" r="7" fill="#ee5a4d" />
          <path d="M19 33l4 3 4-3M38 25l3 3 3-3" stroke={LEAF_DARK} strokeWidth="2" fill="none" strokeLinecap="round" />
          <path d="M32 24c-4-6-10-8-14-7 2 6 8 9 14 7z" fill={LEAF} />
        </g>
      );
    case "rice":
      return (
        <g>
          <path d="M20 56c2-18 6-32 16-44M30 56c1-14 5-26 12-34M40 56c0-12 3-20 8-27" stroke={STEM} strokeWidth="2.6" fill="none" strokeLinecap="round" />
          <path d="M36 12c3 1 5 3 5 7M42 22c3 0 5 2 6 6M48 29c3 0 4 2 5 5" stroke="#d9a441" strokeWidth="3" fill="none" strokeLinecap="round" />
        </g>
      );
    case "groundnut":
      return (
        <g>
          <path d="M32 54V26" stroke={STEM} strokeWidth="3" strokeLinecap="round" />
          <g fill={LEAF}>
            <ellipse cx="22" cy="26" rx="8" ry="5" transform="rotate(-25 22 26)" />
            <ellipse cx="42" cy="26" rx="8" ry="5" transform="rotate(25 42 26)" />
            <ellipse cx="24" cy="38" rx="7" ry="4.5" transform="rotate(-15 24 38)" />
            <ellipse cx="40" cy="38" rx="7" ry="4.5" transform="rotate(15 40 38)" />
          </g>
          <ellipse cx="32" cy="58" rx="6" ry="3.4" fill="#c99a5b" />
        </g>
      );
    default:
      return (
        <g>
          <path d="M32 56V30" stroke={STEM} strokeWidth="3.4" strokeLinecap="round" />
          <path d="M32 40c-12 0-19-8-19-20 12 0 19 8 19 20z" fill={LEAF} />
          <path d="M32 32c0-12 7-19 19-19 0 12-7 19-19 19z" fill={LEAF_DARK} />
        </g>
      );
  }
}

/** Pastille illustrée de la culture (un dessin par grande famille, repli : jeune pousse). */
export function CropArt({ crop, size = 44 }: { crop: string | null | undefined; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      <ellipse cx="32" cy="58" rx="22" ry="4.5" fill={SOIL} opacity="0.55" />
      <CropShape kind={cropKind(crop)} />
    </svg>
  );
}

/** Sillons en perspective : motif de fond, qui donne la profondeur d'un champ cultivé. */
export function Furrows({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 400 120"
      preserveAspectRatio="xMidYMax slice"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M200 0L-40 120" opacity="0.3" />
        <path d="M200 0L40 120" opacity="0.4" />
        <path d="M200 0L120 120" opacity="0.5" />
        <path d="M200 0V120" opacity="0.55" />
        <path d="M200 0L280 120" opacity="0.5" />
        <path d="M200 0L360 120" opacity="0.4" />
        <path d="M200 0L440 120" opacity="0.3" />
      </g>
    </svg>
  );
}

export type SkyKind = "dry" | "light" | "rain";

const DROPS = [
  { x: 54, delay: "art-delay-0" },
  { x: 72, delay: "art-delay-2" },
  { x: 90, delay: "art-delay-1" },
  { x: 108, delay: "art-delay-3" },
  { x: 126, delay: "art-delay-0" },
] as const;

/** Soleil, nuage ou pluie animés (rayons qui tournent, nuage qui dérive, gouttes qui tombent). */
export function SkyArt({ kind, size = 160 }: { kind: SkyKind; size?: number }) {
  const uid = useId().replace(/:/g, "");
  const [sunId, cloudId] = [`sun${uid}`, `cloud${uid}`];
  const showSun = kind !== "rain";
  const showCloud = kind !== "dry";
  return (
    <svg width={size} height={size} viewBox="0 0 180 180" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <radialGradient id={sunId} cx="35%" cy="30%" r="80%">
          <stop offset="0" stopColor="#fff3b0" />
          <stop offset="0.6" stopColor="#ffc93c" />
          <stop offset="1" stopColor="#f59f1b" />
        </radialGradient>
        <linearGradient id={cloudId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#d4e0ec" />
        </linearGradient>
      </defs>
      {showSun ? (
        <g>
          <g className="art-spin" stroke="#ffc93c" strokeWidth="5" strokeLinecap="round">
            {Array.from({ length: 10 }, (_, i) => {
              const angle = (i * 36 * Math.PI) / 180;
              const [cx, cy] = [kind === "light" ? 66 : 90, kind === "light" ? 66 : 82];
              return (
                <line
                  key={i}
                  x1={cx + Math.cos(angle) * 40}
                  y1={cy + Math.sin(angle) * 40}
                  x2={cx + Math.cos(angle) * 54}
                  y2={cy + Math.sin(angle) * 54}
                />
              );
            })}
          </g>
          <circle cx={kind === "light" ? 66 : 90} cy={kind === "light" ? 66 : 82} r="30" fill={`url(#${sunId})`} />
        </g>
      ) : null}
      {showCloud ? (
        <g className="art-drift">
          <path
            d="M52 124a22 22 0 0 1 4-43 30 30 0 0 1 57-4 26 26 0 0 1 9 51z"
            fill={`url(#${cloudId})`}
            stroke="#b9c9da"
            strokeWidth="1.5"
          />
        </g>
      ) : null}
      {kind === "rain" ? (
        <g stroke="#4aa3ee" strokeWidth="4" strokeLinecap="round">
          {DROPS.map((d) => (
            <line key={d.x} x1={d.x} y1="138" x2={d.x - 6} y2="154" className={`art-fall ${d.delay}`} />
          ))}
        </g>
      ) : null}
    </svg>
  );
}

/** Conseiller agronome : buste en chapeau de paille, tablette à la main. Pastille ronde, 56 px par défaut. */
export function AdvisorAvatar({ size = 56 }: { size?: number }) {
  const bgId = `adv${useId().replace(/:/g, "")}`;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={bgId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#9be37f" />
          <stop offset="1" stopColor="#1f7a34" />
        </linearGradient>
      </defs>
      <circle cx="32" cy="32" r="31" fill={`url(#${bgId})`} />
      <path d="M10 60c1-12 9-18 22-18s21 6 22 18" fill="#f4f8f1" />
      <path d="M26 44l6 7 6-7" stroke="#1f7a34" strokeWidth="2.2" fill="none" strokeLinejoin="round" />
      <circle cx="32" cy="30" r="9" fill="#e0b48a" />
      <path d="M13 25c4-1 8-3 19-3s15 2 19 3c-1 4-9 5-19 5s-18-1-19-5z" fill="#e8c25f" />
      <path d="M22 24c1-9 20-9 20 0z" fill="#f0d27a" />
      <path d="M22 24h20" stroke="#1f7a34" strokeWidth="2.2" />
      <circle cx="28.5" cy="31" r="1.1" fill="#3b2a1a" />
      <circle cx="35.5" cy="31" r="1.1" fill="#3b2a1a" />
      <path d="M29 34.6c1.8 1.5 4.2 1.5 6 0" stroke="#3b2a1a" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      <path d="M49 44c3-7 8-9 11-9-1 5-5 9-11 9z" fill="#c9f0a8" />
    </svg>
  );
}
