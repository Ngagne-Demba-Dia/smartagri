import { TrapsView } from "@/features/traps/TrapsView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("traps");

export default async function TrapsPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <TrapsView initialDeviceId={firstParam(sp.kit)} />;
}
