/** Clés React Query des services d'IA ; préfixe commun pour invalider tout un objet métier. */
export const aiKeys = {
  weather: (fieldId: string, days: number) => ["fields", fieldId, "weather", { days }] as const,
  soilForecast: (fieldId: string) => ["fields", fieldId, "soil-forecast"] as const,
  irrigationNeed: (fieldId: string) => ["fields", fieldId, "irrigation-need"] as const,
  irrigationPlan: (farmId: string, date: string) => ["farms", farmId, "irrigation-plan", { date }] as const,
  recommendations: (fieldId: string) => ["fields", fieldId, "recommendations"] as const,
  fertilization: (fieldId: string) => ["fields", fieldId, "fertilization"] as const,
  kitParameters: (deviceId: string) => ["devices", deviceId, "parameters"] as const,
  pestRisk: (fieldId: string) => ["fields", fieldId, "pest-risk"] as const,
  trapCounts: (deviceId: string, from: string, to: string) => ["devices", deviceId, "trap-counts", { from, to }] as const,
  vegetation: (fieldId: string, from: string, to: string) => ["fields", fieldId, "vegetation", { from, to }] as const,
  yieldForecast: (fieldId: string) => ["fields", fieldId, "yield-forecast"] as const,
  deviceHealth: (deviceId: string) => ["devices", deviceId, "health"] as const,
  alerts: (status: string) => ["alerts", { status }] as const,
  kpis: (from: string, to: string) => ["reports", "kpis", { from, to }] as const,
  prices: (crop: string, market: string) => ["markets", "prices", { crop, market }] as const,
  mapLayers: (farmId: string, layers: string) => ["farms", farmId, "map", { layers }] as const,
};
