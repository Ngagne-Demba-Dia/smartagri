import { EquipmentView } from "@/features/equipment/EquipmentView";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("equipment");

export default function EquipmentPage() {
  return <EquipmentView />;
}
