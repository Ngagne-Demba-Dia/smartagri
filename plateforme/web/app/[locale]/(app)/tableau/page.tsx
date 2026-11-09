import { Dashboard } from "@/features/dashboard/Dashboard";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("dashboard");

/** Écran A : tableau de bord (KPI, alertes, prévisions des services IA avec provenance). */
export default function DashboardPage() {
  return <Dashboard />;
}
