import { FieldsList } from "@/features/fields/FieldsList";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("fields");

/** Écran C : liste des parcelles ; ?exploitation=<id> filtre sur une exploitation. */
export default async function FieldsPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <FieldsList farmId={firstParam(sp.exploitation)} />;
}
