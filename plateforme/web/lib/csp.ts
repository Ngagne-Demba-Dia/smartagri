/**
 * Content-Security-Policy des pages (doc 10 §7) : aucun script en ligne, aucun script tiers,
 * pas de 'unsafe-eval' en production. Le nonce est généré par requête dans middleware.ts ;
 * Next.js le lit dans l'en-tête de requête Content-Security-Policy et l'applique à ses scripts.
 */
export function buildCsp(nonce: string, isDev: boolean): string {
  // React 19 en développement reconstruit les piles d'appel avec eval : autorisé en dev seulement.
  const devEval = isDev ? " 'unsafe-eval'" : "";
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${devEval}`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "media-src 'self' blob:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "manifest-src 'self'",
  ];
  if (!isDev) directives.push("upgrade-insecure-requests");
  return directives.join("; ");
}

/** Nonce de 128 bits, encodé en base64 (Web Crypto, disponible dans le runtime Edge). */
export function createNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}
