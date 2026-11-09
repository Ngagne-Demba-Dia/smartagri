import { PestRiskView } from "@/features/pest-risk/PestRiskView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("pestRisk");

export default async function PestRiskPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <PestRiskView initialFieldId={firstParam(sp.parcelle)} />;
}
