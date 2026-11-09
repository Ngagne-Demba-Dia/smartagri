import { CampaignsView } from "@/features/campaigns/CampaignsView";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("campaigns");

export default function CampaignsPage() {
  return <CampaignsView />;
}
