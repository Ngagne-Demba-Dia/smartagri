const WIDTH = 120;
const HEIGHT = 32;
const PAD = 2;

/** Points « x,y » d'une courbe normalisée dans WIDTH × HEIGHT ; une série plate est tracée au milieu. */
export function sparklinePoints(values: readonly number[]): string {
  if (values.length === 0) return "";
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo;
  const step = values.length > 1 ? (WIDTH - 2 * PAD) / (values.length - 1) : 0;
  return values
    .map((v, i) => {
      const y = span === 0 ? HEIGHT / 2 : HEIGHT - PAD - ((v - lo) / span) * (HEIGHT - 2 * PAD);
      return `${(PAD + i * step).toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

/** Mini-courbe de tendance : le chiffre reste dans le texte voisin, la courbe porte un résumé accessible. */
export function Sparkline({ values, label }: { values: readonly number[]; label: string }) {
  if (values.length < 2) return null;
  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="block h-8 w-full max-w-40 text-g"
    >
      <polyline
        points={sparklinePoints(values)}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
