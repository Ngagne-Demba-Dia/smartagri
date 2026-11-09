import { CropsView } from "@/features/crops/CropsView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("crops");

export default async function CropsPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <CropsView initialFieldId={firstParam(sp.parcelle)} />;
}
