import { IrrigationPlanView } from "@/features/irrigation-plan/IrrigationPlanView";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("irrigationPlan");

export default async function IrrigationPlanPage() {
  return <IrrigationPlanView />;
}
