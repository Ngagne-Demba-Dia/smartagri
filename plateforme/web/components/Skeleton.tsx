import type { ReactNode } from "react";

/** Bloc de chargement : même gabarit que le contenu attendu, pour que la page ne saute pas à l'arrivée des données. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

/** Zone annoncée une fois aux lecteurs d'écran (role=status) : le contenu animé reste muet. */
export function SkeletonRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="status" aria-busy="true" className="flex flex-col gap-3">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

const KPI_PLACEHOLDERS = [0, 1, 2, 3];
const CARD_PLACEHOLDERS = [0, 1];

/** Gabarit « tableau de bord » : rangée de KPI puis cartes. Convient à la plupart des écrans. */
export function SkeletonPage({ label }: { label: string }) {
  return (
    <SkeletonRegion label={label}>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {KPI_PLACEHOLDERS.map((i) => (
          <Skeleton key={i} className="h-24 rounded-card" />
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {CARD_PLACEHOLDERS.map((i) => (
          <Skeleton key={i} className="h-56 rounded-card" />
        ))}
      </div>
    </SkeletonRegion>
  );
}
