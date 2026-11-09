import { AlertsLog } from "@/features/alerts/AlertsLog";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("alerts");

export default function AlertsPage() {
  return <AlertsLog />;
}
