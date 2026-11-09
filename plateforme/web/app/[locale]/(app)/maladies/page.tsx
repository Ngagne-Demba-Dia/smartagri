import { DiagnosisView } from "@/features/diagnosis/DiagnosisView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("diseases");

export default async function DiseasesPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <DiagnosisView initialFieldId={firstParam(sp.parcelle)} />;
}
