const BASE64_CHUNK = 0x8000;

/** Encodage base64 d'un fichier binaire (audio, image), par blocs pour ne pas saturer la pile d'appels. */
export function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += BASE64_CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + BASE64_CHUNK));
  }
  return btoa(binary);
}
