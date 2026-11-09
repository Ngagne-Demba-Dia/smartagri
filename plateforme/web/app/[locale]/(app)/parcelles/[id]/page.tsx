import { FieldDetail } from "@/features/fields/FieldDetail";
import { moduleMetadata } from "@/lib/server/page-metadata";

export const generateMetadata = () => moduleMetadata("fields");

/** Écran C (détail) : capteurs, courbe d'humidité avec seuils, état de la pompe, réglage des seuils. */
export default async function FieldDetailPage({ params }: { params: Promise<{ locale: string; id: string }> }) {
  const { id } = await params;
  return <FieldDetail fieldId={id} />;
}
