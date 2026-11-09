/** Marque : feuille dans un carré arrondi lumineux, puis le nom. Le carré porte la couleur d'accent de la marque. */
export function BrandMark({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
      className="drop-shadow-[0_4px_10px_rgb(23_89_31_/_0.45)]"
    >
      <rect width="32" height="32" rx="10" className="fill-accent" />
      <rect width="32" height="32" rx="10" className="fill-white/15" />
      <path
        d="M9 23c0-8 5-13 14-14-.6 8.6-5.6 13.6-14 14zM9 23l7-7"
        fill="none"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="stroke-white"
      />
    </svg>
  );
}

/** `tone="light"` : texte blanc, pour la poser sur la photo (connexion). */
export function Brand({ name, tone = "default" }: { name: string; tone?: "default" | "light" }) {
  return (
    <span
      className={`flex items-center gap-2 font-bold tracking-tight ${tone === "light" ? "text-white" : "text-ink"}`}
    >
      <BrandMark />
      <span>{name}</span>
    </span>
  );
}
