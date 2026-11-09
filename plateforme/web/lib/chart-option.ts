/**
 * Description d'un graphique conforme à doc 10 §5, indépendante de la bibliothèque de rendu
 * (fonctions pures, testées). Le rendu Recharts est dans components/chart/Chart.tsx.
 * Règles appliquées ici, pas au cas par cas dans les écrans :
 * - un seul axe Y (jamais de double axe) et l'unité écrite au-dessus du tracé ;
 * - légende seulement à partir de deux éléments nommés (séries ou bande) ;
 * - lignes de 2 px, points de 8 px tant qu'ils restent lisibles, barres de 24 px au plus aux coins arrondis ;
 * - lignes de référence (seuils) en tirets, toujours étiquetées ;
 * - bande p10–p90 optionnelle (doc 16 §9.2, confiance de type « interval ») ;
 * - couleurs des séries dans un ordre fixe, lues dans les jetons CSS (thème clair et sombre) ;
 * - résumé en une phrase et vue en tableau pour les lecteurs d'écran.
 */
export interface ChartSeriesSpec {
  id: string;
  name: string;
  kind: "line" | "bar";
  values: ReadonlyArray<number | null>;
}

export interface ReferenceLine {
  value: number;
  label: string;
}

/** Intervalle p10–p90 autour d'une série (jamais inventé : absent si le modèle n'en fournit pas). */
export interface ChartBand {
  id: string;
  name: string;
  low: ReadonlyArray<number | null>;
  high: ReadonlyArray<number | null>;
}

export interface ChartSpec {
  categories: readonly string[];
  series: readonly ChartSeriesSpec[];
  unit: string;
  yMin?: number;
  yMax?: number;
  references?: readonly ReferenceLine[];
  band?: ChartBand;
  /** Résumé en une phrase pour les lecteurs d'écran (ex. « Humidité du sol sur 7 jours, de 18 à 41 % »). */
  summary: string;
}

export const BAR_MAX_WIDTH = 24;
export const LINE_WIDTH = 2;
export const DOT_RADIUS = 4;
/** Au-delà, les points ne sont plus dessinés (la ligne seule reste lisible). */
export const MAX_SYMBOLS = 31;
/** Couleurs catégorielles dans l'ordre fixe (app/globals.css) ; une 3e série passe en petits multiples. */
export const SERIES_COLORS = ["var(--series-1)", "var(--series-2)"] as const;
export const BAND_OPACITY = 0.18;

export type ValueFormatter = (value: number | null) => string;

export type ChartCell = string | number | null | [number, number];
export type ChartRow = { category: string } & Record<string, ChartCell>;

/** Couleur de la série n° `index` ; au-delà de la palette validée : encre atténuée (jamais une teinte générée). */
export function seriesColor(index: number): string {
  return SERIES_COLORS[index] ?? "var(--mute)";
}

export function legendVisible(spec: ChartSpec): boolean {
  return spec.series.length + (spec.band ? 1 : 0) >= 2;
}

export function showDots(spec: ChartSpec): boolean {
  return spec.categories.length <= MAX_SYMBOLS;
}

export function yDomain(spec: ChartSpec): [number | "auto", number | "auto"] {
  return [spec.yMin ?? "auto", spec.yMax ?? "auto"];
}

function bandCell(band: ChartBand, index: number): [number, number] | null {
  const low = band.low[index];
  const high = band.high[index];
  return low == null || high == null ? null : [low, high];
}

/** Lignes de données pour Recharts : une par catégorie, une clé par série (et la bande en [bas, haut]). */
export function toChartRows(spec: ChartSpec): ChartRow[] {
  return spec.categories.map((category, index) => {
    const row: ChartRow = { category };
    for (const s of spec.series) row[s.id] = s.values[index] ?? null;
    if (spec.band) row[spec.band.id] = bandCell(spec.band, index);
    return row;
  });
}

/** En-têtes de la vue en tableau : séries, puis bornes de la bande si elle existe. */
export function chartTableHeaders(spec: ChartSpec, labels: { low: string; high: string }): string[] {
  const headers = spec.series.map((s) => `${s.name} (${spec.unit})`);
  if (!spec.band) return headers;
  return [...headers, `${spec.band.name} — ${labels.low} (${spec.unit})`, `${spec.band.name} — ${labels.high} (${spec.unit})`];
}

/** Données du graphique en tableau (bouton « Voir en tableau ») : une ligne par catégorie. */
export function chartTableRows(spec: ChartSpec): Array<{ category: string; values: Array<number | null> }> {
  return spec.categories.map((category, i) => {
    const values = spec.series.map((s) => s.values[i] ?? null);
    if (!spec.band) return { category, values };
    return { category, values: [...values, spec.band.low[i] ?? null, spec.band.high[i] ?? null] };
  });
}

/** Phrase annoncée quand le clavier se pose sur un point (zone live). */
export function describePoint(spec: ChartSpec, index: number, formatValue: ValueFormatter): string {
  const parts = spec.series.map((s) => `${s.name} ${formatValue(s.values[index] ?? null)}`);
  const cell = spec.band ? bandCell(spec.band, index) : null;
  if (spec.band && cell) parts.push(`${spec.band.name} ${formatValue(cell[0])} – ${formatValue(cell[1])}`);
  return `${spec.categories[index] ?? ""} : ${parts.join(", ")}`;
}

/** Déplacement clavier : ←/→ d'un point, Début/Fin aux extrémités ; null si la touche n'est pas gérée. */
export function nextPointer(current: number, key: string, count: number): number | null {
  if (count === 0) return null;
  const moves: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1, Home: -count, End: count };
  const step = moves[key];
  if (step === undefined) return null;
  const start = current < 0 ? (step > 0 ? -1 : count) : current;
  return Math.min(count - 1, Math.max(0, start + step));
}
