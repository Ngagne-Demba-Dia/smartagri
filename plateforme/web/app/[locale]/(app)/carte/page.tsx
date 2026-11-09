import { FieldMap } from "@/features/map/FieldMap";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("map");

/** Écran B : carte des parcelles ; ?parcelle=<id> ouvre le panneau d'une parcelle. */
export default async function MapPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <FieldMap initialFieldId={firstParam(sp.parcelle)} />;
}
