import { moistureRamp, type RampStep } from "@/lib/status";

/**
 * Noms de classe écrits en entier : Tailwind ne garde que les classes qu'il trouve telles quelles dans le code
 * (une classe construite par `ramp-${n}` serait retirée du CSS de production).
 */
const RAMP_CLASS: Record<RampStep, string> = {
  0: "ramp-0",
  1: "ramp-1",
  2: "ramp-2",
  3: "ramp-3",
  4: "ramp-4",
  5: "ramp-5",
};

/** Pastille de couleur de l'humidité du sol ; décorative : la valeur est toujours écrite à côté. */
export function RampSwatch({ moisture, size = "md" }: { moisture: number | null; size?: "sm" | "md" }) {
  const box = size === "sm" ? "h-5 w-5" : "h-10 w-10";
  return (
    <span
      className={`${RAMP_CLASS[moistureRamp(moisture)]} ${box} inline-block shrink-0 rounded-btn`}
      aria-hidden="true"
    />
  );
}

export function RampStepSwatch({ step }: { step: RampStep }) {
  return (
    <span className={`${RAMP_CLASS[step]} inline-block h-5 w-5 shrink-0 rounded-btn`} aria-hidden="true" />
  );
}
