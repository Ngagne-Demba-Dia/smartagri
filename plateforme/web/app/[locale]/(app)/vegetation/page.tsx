import { VegetationView } from "@/features/vegetation/VegetationView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("vegetation");

export default async function VegetationPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <VegetationView initialFieldId={firstParam(sp.parcelle)} />;
}
