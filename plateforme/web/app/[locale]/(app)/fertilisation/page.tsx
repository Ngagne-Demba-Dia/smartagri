import { FertilizationView } from "@/features/fertilization/FertilizationView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("fertilization");

export default async function FertilizationPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <FertilizationView initialFieldId={firstParam(sp.parcelle)} />;
}
