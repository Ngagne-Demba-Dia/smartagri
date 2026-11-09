import { YieldView } from "@/features/yield/YieldView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("yield");

export default async function YieldPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <YieldView initialFieldId={firstParam(sp.parcelle)} />;
}
