import { CommunityView } from "@/features/community/CommunityView";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("community");

export default function CommunityPage() {
  return <CommunityView />;
}
