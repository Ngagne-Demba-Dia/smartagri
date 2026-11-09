import { RecommendationsList } from "@/features/recommendations/RecommendationsList";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("recommendations");

/** Écran D : recommandations IA ; ?parcelle=<id> présélectionne une parcelle. */
export default async function RecommendationsPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <RecommendationsList initialFieldId={firstParam(sp.parcelle)} />;
}
