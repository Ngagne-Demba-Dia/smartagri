import { SoilForecastView } from "@/features/soil-forecast/SoilForecastView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("soilForecast");

export default async function SoilForecastPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <SoilForecastView initialFieldId={firstParam(sp.parcelle)} />;
}
