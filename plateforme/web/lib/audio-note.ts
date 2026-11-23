/**
 * Génération d'une note audio WAV (PCM 16 bits, 8 kHz mono) en mémoire pour les messages vocaux
 * (compatible CSP `media-src 'self' blob:` via URL.createObjectURL) et lecture vocale par synthèse du navigateur.
 */

const SAMPLE_RATE = 8000;

export function createVoiceToneWavBlob(durationS = 4, seed = 1): Blob {
  const clamped = Math.max(1, Math.min(30, Math.round(durationS)));
  const numSamples = SAMPLE_RATE * clamped;
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i += 1) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + numSamples * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, SAMPLE_RATE, true);
  view.setUint32(28, SAMPLE_RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, numSamples * 2, true);

  const baseFreq = 165 + (seed % 5) * 18;
  for (let i = 0; i < numSamples; i += 1) {
    const t = i / SAMPLE_RATE;
    const syllable = Math.sin(2 * Math.PI * 3.2 * t) > -0.25 ? 1 : 0.15;
    const pitch = baseFreq + 25 * Math.sin(2 * Math.PI * 1.4 * t);
    const wave =
      0.6 * Math.sin(2 * Math.PI * pitch * t) +
      0.3 * Math.sin(2 * Math.PI * pitch * 2 * t) +
      0.1 * Math.sin(2 * Math.PI * pitch * 3 * t);
    const sample = Math.max(-1, Math.min(1, wave * syllable * 0.35));
    view.setInt16(44 + i * 2, Math.round(sample * 32767), true);
  }

  return new Blob([buffer], { type: "audio/wav" });
}

export function speakText(text: string, lang = "fr-FR"): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  } catch {
    // Certains navigateurs headless désactivent speechSynthesis.
  }
}
