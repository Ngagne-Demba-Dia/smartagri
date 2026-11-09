import { UPLOAD_MAX_RAW_BYTES } from "@/lib/contracts/assistant";
import { encodeWithinLimit, fitWithin } from "@/lib/diagnosis";

/**
 * Réduit la photo avant l'envoi (limite du BFF : 256 Kio de JSON) et la ré-encode en JPEG : les métadonnées
 * (lieu, appareil) sont ainsi retirées. Renvoie null si même la plus petite version reste trop lourde ;
 * lève une erreur si le navigateur ne sait pas lire l'image.
 */
export async function prepareImage(file: Blob): Promise<Blob | null> {
  const bitmap = await createImageBitmap(file);
  try {
    const encode = (maxSide: number, quality: number): Promise<Blob> => {
      const { width, height } = fitWithin(bitmap.width, bitmap.height, maxSide);
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) return Promise.reject(new Error("canvas indisponible"));
      // Le JPEG n'a pas de transparence : fond blanc plutôt que noir pour les PNG et WebP.
      context.fillStyle = "#fff";
      context.fillRect(0, 0, width, height);
      context.drawImage(bitmap, 0, 0, width, height);
      return new Promise((resolve, reject) =>
        canvas.toBlob(
          (blob) => (blob ? resolve(blob) : reject(new Error("encodage impossible"))),
          "image/jpeg",
          quality,
        ),
      );
    };
    return await encodeWithinLimit(encode, UPLOAD_MAX_RAW_BYTES);
  } finally {
    bitmap.close();
  }
}
