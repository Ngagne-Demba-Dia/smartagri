import { ReportsView } from "@/features/reports/ReportsView";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("reports");

export default function ReportsPage() {
  return <ReportsView />;
}
