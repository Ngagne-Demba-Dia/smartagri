const VIEW_WIDTH = 100;
const VIEW_HEIGHT = 8;

export interface MeterMark {
  value: number;
  label: string;
}

/**
 * Jauge horizontale en SVG (la CSP à nonce interdit style="width:…" : la longueur passe par un attribut SVG).
 * role="meter" avec valeur texte : le lecteur d'écran annonce « 42 % », pas seulement une barre.
 */
export function Meter({
  value,
  min = 0,
  max = 100,
  label,
  valueText,
  marks = [],
}: {
  value: number;
  min?: number;
  max?: number;
  label: string;
  valueText: string;
  marks?: readonly MeterMark[];
}) {
  const span = max - min || 1;
  const toX = (v: number) => ((Math.min(max, Math.max(min, v)) - min) / span) * VIEW_WIDTH;
  return (
    <svg
      role="meter"
      aria-label={label}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-valuetext={valueText}
      viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
      preserveAspectRatio="none"
      className="block h-2.5 w-full text-g"
    >
      <rect width={VIEW_WIDTH} height={VIEW_HEIGHT} rx={4} className="fill-ink-soft" />
      <rect width={toX(value)} height={VIEW_HEIGHT} rx={4} className="meter-fill fill-accent" />
      {marks.map((mark) => (
        <line
          key={mark.label}
          x1={toX(mark.value)}
          x2={toX(mark.value)}
          y1={0}
          y2={VIEW_HEIGHT}
          strokeWidth={1}
          className="stroke-ink"
        >
          <title>{mark.label}</title>
        </line>
      ))}
    </svg>
  );
}
