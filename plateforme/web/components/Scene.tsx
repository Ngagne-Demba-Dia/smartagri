/**
 * Décor immersif fixe derrière toute l'application : la photo de champ, un voile de lisibilité (jetons --veil),
 * une teinte propre à l'écran et deux halos de lumière diffuse. Image simple <img> : next/image ajouterait un
 * attribut style que la CSP à nonce bloque. Le recadrage par écran vient de `data-scene` sur un ancêtre.
 */
export function Scene() {
  return (
    <div aria-hidden="true" className="scene">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/img/champ-hero.webp" alt="" width={1280} height={855} className="scene-photo" fetchPriority="high" />
      <div className="scene-tint" />
      <div className="scene-veil" />
      <div className="scene-glow" />
      <div className="scene-glow scene-glow-b" />
    </div>
  );
}
