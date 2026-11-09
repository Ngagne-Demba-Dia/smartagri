/**
 * Service 14 — water_savings : bloc kpis.water_savings de GET /v1/reports/kpis (existante), méthode des
 * parcelles témoins. L'export CSV est un lien direct servi par le BFF avec les cookies de session.
 */
import { useQuery } from "@tanstack/react-query";

import { buildQuery } from "@/lib/api";
import { KpiReportSchema } from "@/lib/contracts/org";

import { getContract, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export interface ReportWindow {
  from: string;
  to: string;
}

const reportQuery = (window: ReportWindow) => ({ scope: "org", from: window.from, to: window.to });

export function fetchKpis(window: ReportWindow, options?: CallOptions) {
  return getContract("water_savings", KpiReportSchema, "/v1/reports/kpis", reportQuery(window), options);
}

export function exportCsvUrl(window: ReportWindow): string {
  return `/api/v1/reports/export.csv${buildQuery(reportQuery(window))}`;
}

export function useKpis(window: ReportWindow) {
  return useQuery({
    queryKey: aiKeys.kpis(window.from, window.to),
    staleTime: staleFor("water_savings"),
    queryFn: ({ signal }) => fetchKpis(window, { signal }),
  });
}
