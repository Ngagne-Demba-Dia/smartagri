import { AssistantChat } from "@/features/assistant/AssistantChat";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("assistant");

/** Écran E : assistant IA (réponses sourcées, abstention affichée). */
export default function AssistantPage() {
  return <AssistantChat />;
}
