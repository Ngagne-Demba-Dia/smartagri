import { IrrigationView } from "@/features/irrigation/IrrigationView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("irrigation");

export default async function IrrigationPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <IrrigationView initialFieldId={firstParam(sp.parcelle)} />;
}
