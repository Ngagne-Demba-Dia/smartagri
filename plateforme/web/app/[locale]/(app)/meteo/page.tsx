import { WeatherView } from "@/features/weather/WeatherView";
import { firstParam, type PageSearchParams } from "@/lib/nav";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("weather");

export default async function WeatherPage({ searchParams }: { searchParams: PageSearchParams }) {
  const sp = await searchParams;
  return <WeatherView initialFieldId={firstParam(sp.parcelle)} />;
}
