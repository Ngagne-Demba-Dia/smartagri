import { KitView } from "@/features/kit/KitView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("kit");

export default async function KitPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <KitView initialDeviceId={firstParam(sp.kit)} />;
}
