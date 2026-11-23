/**
 * Géographie du Sénégal pour la carte nationale (module 4) :
 * - Contour terrestre du Sénégal (frontières et façade atlantique) ;
 * - Cours d'eau majeurs (Fleuve Sénégal, Lac de Guiers, Fleuve Casamance, Fleuve Gambie) ;
 * - 6 grandes zones agro-écologiques (Niayes, Vallée du Fleuve, Bassin Arachidier, Ferlo, Sénégal Oriental, Casamance) ;
 * - Périmètres et champs représentatifs par zone agro-écologique.
 * 100 % local (CSP 'self', aucun serveur de tuiles externe requis).
 */
import type { LatLon, LatLonBounds } from "./map-style";

export const SENEGAL_BOUNDS: LatLonBounds = [
  [12.2, -17.65],
  [16.75, -11.3],
];

/** Contour simplifié fidèle du Sénégal [latitude, longitude]. */
export const SENEGAL_BORDER: readonly LatLon[] = [
  [16.05, -16.51], // Saint-Louis
  [15.65, -16.55], // Potou / Lompoul
  [15.15, -16.92], // Mboro / Kayar
  [14.74, -17.53], // Dakar / Pointe des Almadies
  [14.67, -17.43], // Baie de Hann
  [14.45, -17.02], // Mbour / Saly
  [14.16, -16.85], // Joal-Fadiouth
  [13.65, -16.55], // Sine-Saloum / Karang
  [13.58, -15.9],  // Frontière nord Gambie (Kaolack sud)
  [13.78, -14.85], // Koungheul sud
  [13.45, -13.75], // Tambacounda ouest / contournement est Gambie
  [13.28, -13.85], // Vélingara nord
  [13.15, -15.55], // Frontière sud Gambie (Sédhiou nord)
  [13.1, -16.68],  // Diouloulou / Kafountine
  [12.35, -16.73], // Cap Skirring / Basse-Casamance
  [12.42, -15.8],  // Ziguinchor sud
  [12.68, -14.9],  // Kolda sud
  [12.65, -13.7],  // Vélingara sud
  [12.35, -12.2],  // Kédougou ouest (frontière Guinée)
  [12.42, -11.42], // Kédougou est / Saraya (frontière Mali)
  [13.4, -11.65],  // Falémé
  [14.46, -12.21], // Kidira
  [14.9, -12.46],  // Bakel
  [15.65, -13.25], // Matam
  [16.12, -13.85], // Saldé / Île à Morphil
  [16.65, -14.96], // Podor
  [16.46, -15.7],  // Richard-Toll / Dagana
  [16.25, -16.25], // Ross-Béthio / Ndiol
  [16.05, -16.51], // Fermeture Saint-Louis
];

export interface SenegalRiver {
  id: string;
  name: string;
  path: readonly LatLon[];
}

export const SENEGAL_RIVERS: readonly SenegalRiver[] = [
  {
    id: "fleuve-senegal",
    name: "Fleuve Sénégal",
    path: [
      [16.05, -16.5],
      [16.22, -16.28],
      [16.46, -15.7],
      [16.65, -14.96],
      [16.12, -13.85],
      [15.65, -13.25],
      [14.9, -12.46],
    ],
  },
  {
    id: "lac-guiers",
    name: "Lac de Guiers",
    path: [
      [16.46, -15.7],
      [16.25, -15.82],
      [15.92, -15.88],
    ],
  },
  {
    id: "fleuve-casamance",
    name: "Fleuve Casamance",
    path: [
      [12.55, -16.7],
      [12.58, -16.27],
      [12.72, -15.55],
      [12.88, -14.95],
    ],
  },
  {
    id: "fleuve-gambie-amont",
    name: "Fleuve Gambie (amont)",
    path: [
      [13.45, -13.75],
      [13.1, -13.2],
      [12.56, -12.18],
    ],
  },
];

export type AgroZoneId = "niayes" | "vallee" | "arachide" | "ferlo" | "oriental" | "casamance";

export interface AgroZone {
  id: AgroZoneId;
  name: string;
  regions: string;
  crops: string;
  waterSource: string;
  phRange: string;
  avgMoisturePct: number;
  avgNdvi: number;
  className: string;
  center: LatLon;
  polygon: readonly LatLon[];
}

export const SENEGAL_ZONES: readonly AgroZone[] = [
  {
    id: "niayes",
    name: "Zone des Niayes",
    regions: "Dakar · Thiès (Mboro) · Louga (Potou) · Saint-Louis",
    crops: "Oignon, Tomate, Chou, Pomme de terre, Carotte",
    waterSource: "Forages & nappes interdunaires",
    phRange: "6,8 – 7,6 pH",
    avgMoisturePct: 36,
    avgNdvi: 0.62,
    className: "map-zone-niayes",
    center: [15.32, -16.72],
    polygon: [
      [14.74, -17.48],
      [15.15, -16.92],
      [15.95, -16.52],
      [15.95, -16.18],
      [15.15, -16.55],
      [14.74, -17.05],
    ],
  },
  {
    id: "vallee",
    name: "Vallée du Fleuve Sénégal",
    regions: "Saint-Louis (Ndiol, Ross-Béthio) · Dagana · Podor · Matam",
    crops: "Riz irrigué, Oignon Violet de Galmi, Tomate industrielle",
    waterSource: "Fleuve Sénégal & Lac de Guiers",
    phRange: "6,4 – 6,9 pH",
    avgMoisturePct: 44,
    avgNdvi: 0.68,
    className: "map-zone-vallee",
    center: [16.25, -14.85],
    polygon: [
      [16.02, -16.48],
      [16.28, -16.2],
      [16.48, -15.68],
      [16.64, -14.95],
      [16.1, -13.82],
      [15.55, -13.2],
      [15.3, -13.55],
      [15.85, -14.35],
      [16.15, -15.2],
      [15.92, -16.15],
    ],
  },
  {
    id: "arachide",
    name: "Bassin Arachidier",
    regions: "Thiès · Diourbel (Touba) · Fatick · Kaolack · Kaffrine",
    crops: "Arachide, Mil, Niébé, Pastèque, Maraîchage",
    waterSource: "Pluvial & forages profonds",
    phRange: "6,6 – 7,3 pH",
    avgMoisturePct: 29,
    avgNdvi: 0.48,
    className: "map-zone-arachide",
    center: [14.35, -15.85],
    polygon: [
      [14.45, -16.98],
      [15.1, -16.5],
      [15.2, -15.4],
      [14.65, -14.45],
      [13.8, -14.75],
      [13.62, -15.95],
      [13.68, -16.52],
    ],
  },
  {
    id: "ferlo",
    name: "Zone Sylvo-Pastorale (Ferlo)",
    regions: "Louga · Linguère · Ranérou · Matam intérieur",
    crops: "Niébé, Mil, Cultures fourragères, Gomme arabique",
    waterSource: "Forages pastoraux & mares temporaires",
    phRange: "7,0 – 7,8 pH",
    avgMoisturePct: 22,
    avgNdvi: 0.34,
    className: "map-zone-ferlo",
    center: [15.4, -14.85],
    polygon: [
      [15.92, -16.12],
      [16.12, -15.2],
      [15.82, -14.35],
      [15.28, -13.55],
      [14.65, -13.6],
      [14.68, -14.45],
      [15.2, -15.4],
      [15.12, -16.45],
    ],
  },
  {
    id: "oriental",
    name: "Sénégal Oriental & Haute-Casamance",
    regions: "Tambacounda · Kédougou · Vélingara · Kolda Est",
    crops: "Coton, Maïs, Sorgho, Banane, Anacarde",
    waterSource: "Fleuve Gambie, Falémé & nappes",
    phRange: "6,2 – 6,8 pH",
    avgMoisturePct: 41,
    avgNdvi: 0.59,
    className: "map-zone-oriental",
    center: [13.45, -12.75],
    polygon: [
      [14.65, -14.4],
      [14.62, -13.55],
      [15.25, -13.15],
      [14.88, -12.46],
      [13.4, -11.65],
      [12.42, -11.45],
      [12.38, -12.2],
      [12.66, -13.7],
      [13.45, -13.75],
      [13.8, -14.7],
    ],
  },
  {
    id: "casamance",
    name: "Basse & Moyenne Casamance",
    regions: "Ziguinchor · Bignona · Oussouye · Sédhiou · Kolda",
    crops: "Riz de bas-fond, Mangue, Agrumes, Anacarde, Maraîchage",
    waterSource: "Fleuve Casamance, bolongs & pluviométrie élevée",
    phRange: "5,8 – 6,6 pH",
    avgMoisturePct: 54,
    avgNdvi: 0.76,
    className: "map-zone-casamance",
    center: [12.78, -15.65],
    polygon: [
      [13.1, -16.68],
      [13.15, -15.55],
      [13.26, -13.88],
      [12.66, -13.72],
      [12.68, -14.9],
      [12.42, -15.8],
      [12.35, -16.73],
    ],
  },
];

export interface RegionalFieldSpot {
  id: string;
  name: string;
  zoneId: AgroZoneId;
  zoneName: string;
  crop: string;
  areaHa: number;
  moisturePct: number;
  ndvi: number;
  ph: number;
  kitSerial: string;
  position: LatLon;
}

/**
 * Champs et périmètres agricoles positionnés sur la carte du Sénégal à travers les différentes zones,
 * avec décalage visuel léger pour que les parcelles proches (Mboro 1/2/3, Potou 1/2, Ndiol 1/2) soient
 * toutes distinctes à l'échelle nationale.
 */
export const SENEGAL_FIELD_SPOTS: readonly RegionalFieldSpot[] = [
  {
    id: "fld-mboro-1",
    name: "Mboro 1 (Niayes Sud)",
    zoneId: "niayes",
    zoneName: "Zone des Niayes",
    crop: "Oignon Violet de Galmi",
    areaHa: 0.5,
    moisturePct: 26,
    ndvi: 0.61,
    ph: 6.8,
    kitSerial: "SA92-0001",
    position: [15.14, -16.88],
  },
  {
    id: "fld-mboro-2",
    name: "Mboro 2 (Niayes Centre)",
    zoneId: "niayes",
    zoneName: "Zone des Niayes",
    crop: "Tomate maraîchère",
    areaHa: 0.8,
    moisturePct: 42,
    ndvi: 0.67,
    ph: 6.8,
    kitSerial: "SA92-0002",
    position: [15.28, -16.72],
  },
  {
    id: "fld-mboro-3",
    name: "Mboro 3 (Kayar / Notto)",
    zoneId: "niayes",
    zoneName: "Zone des Niayes",
    crop: "Chou pommé",
    areaHa: 0.4,
    moisturePct: 35,
    ndvi: 0.58,
    ph: 6.9,
    kitSerial: "SA92-0001",
    position: [14.95, -17.05],
  },
  {
    id: "fld-potou-1",
    name: "Potou 1 (Niayes Nord · Louga)",
    zoneId: "niayes",
    zoneName: "Zone des Niayes",
    crop: "Carotte Nantaise",
    areaHa: 1.2,
    moisturePct: 33,
    ndvi: 0.59,
    ph: 7.6,
    kitSerial: "SA92-0003",
    position: [15.72, -16.48],
  },
  {
    id: "fld-potou-2",
    name: "Potou 2 (Lompoul · Kébémer)",
    zoneId: "niayes",
    zoneName: "Zone des Niayes",
    crop: "Pomme de terre",
    areaHa: 0.9,
    moisturePct: 39,
    ndvi: 0.64,
    ph: 7.5,
    kitSerial: "SA92-0004",
    position: [15.56, -16.32],
  },
  {
    id: "fld-ndiol-1",
    name: "Ndiol 1 (Ross-Béthio · Vallée)",
    zoneId: "vallee",
    zoneName: "Vallée du Fleuve Sénégal",
    crop: "Oignon Violet de Galmi",
    areaHa: 1.0,
    moisturePct: 38,
    ndvi: 0.37,
    ph: 6.4,
    kitSerial: "SA92-0101",
    position: [16.18, -16.32],
  },
  {
    id: "fld-ndiol-2",
    name: "Ndiol 2 (Delta · Saint-Louis)",
    zoneId: "vallee",
    zoneName: "Vallée du Fleuve Sénégal",
    crop: "Riz irrigué",
    areaHa: 0.6,
    moisturePct: 48,
    ndvi: 0.71,
    ph: 6.5,
    kitSerial: "SA92-0102",
    position: [16.36, -15.88],
  },
  {
    id: "fld-podor-1",
    name: "Périmètre de Podor (Moyenne Vallée)",
    zoneId: "vallee",
    zoneName: "Vallée du Fleuve Sénégal",
    crop: "Riz & Oignon",
    areaHa: 2.4,
    moisturePct: 45,
    ndvi: 0.69,
    ph: 6.5,
    kitSerial: "SA92-0201",
    position: [16.58, -14.95],
  },
  {
    id: "fld-kaolack-1",
    name: "Périmètre de Kaolack (Bassin Arachidier)",
    zoneId: "arachide",
    zoneName: "Bassin Arachidier",
    crop: "Arachide & Pastèque",
    areaHa: 1.8,
    moisturePct: 29,
    ndvi: 0.49,
    ph: 6.9,
    kitSerial: "SA92-0301",
    position: [14.18, -16.05],
  },
  {
    id: "fld-touba-1",
    name: "Périmètre de Diourbel / Touba",
    zoneId: "arachide",
    zoneName: "Bassin Arachidier",
    crop: "Mil & Niébé",
    areaHa: 1.5,
    moisturePct: 27,
    ndvi: 0.46,
    ph: 7.0,
    kitSerial: "SA92-0302",
    position: [14.82, -15.88],
  },
  {
    id: "fld-linguere-1",
    name: "Périmètre de Linguère (Ferlo)",
    zoneId: "ferlo",
    zoneName: "Zone Sylvo-Pastorale (Ferlo)",
    crop: "Niébé & Fourrage",
    areaHa: 2.0,
    moisturePct: 22,
    ndvi: 0.35,
    ph: 7.3,
    kitSerial: "SA92-0401",
    position: [15.39, -15.11],
  },
  {
    id: "fld-tamba-1",
    name: "Périmètre de Tambacounda (Sénégal Oriental)",
    zoneId: "oriental",
    zoneName: "Sénégal Oriental & Haute-Casamance",
    crop: "Maïs & Banane",
    areaHa: 2.2,
    moisturePct: 41,
    ndvi: 0.6,
    ph: 6.6,
    kitSerial: "SA92-0501",
    position: [13.76, -13.66],
  },
  {
    id: "fld-ziguinchor-1",
    name: "Périmètre de Ziguinchor (Casamance)",
    zoneId: "casamance",
    zoneName: "Basse & Moyenne Casamance",
    crop: "Riz & Mangue",
    areaHa: 1.9,
    moisturePct: 54,
    ndvi: 0.77,
    ph: 6.2,
    kitSerial: "SA92-0601",
    position: [12.58, -16.27],
  },
];
