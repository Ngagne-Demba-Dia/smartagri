import { MarketsView } from "@/features/markets/MarketsView";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("markets");

export default async function MarketsPage() {
  return <MarketsView />;
}
