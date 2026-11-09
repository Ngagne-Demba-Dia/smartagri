#!/usr/bin/env node
/**
 * Contrôle des contrastes WCAG 2.1 AA des jetons de couleur (npm run contrast).
 * Lit app/globals.css : bloc `:root` (clair) et bloc `:root[data-theme="dark"]` (sombre).
 * Texte : 4,5 minimum ; éléments d'interface et grands textes : 3 minimum. Code de sortie 1 au moindre échec.
 */
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

function block(selector) {
  const start = css.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`Bloc introuvable : ${selector}`);
  const end = css.indexOf("}", start);
  const tokens = {};
  for (const m of css.slice(start, end).matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g))
    tokens[m[1]] = m[2];
  return tokens;
}

const channel = (v) => {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
const luminance = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
};
const ratio = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

/** [premier plan, arrière-plan, minimum, usage] */
const PAIRS = [
  ["ink", "bg", 4.5, "texte courant sur la page"],
  ["ink", "card", 4.5, "texte courant sur carte"],
  ["mute", "bg", 4.5, "texte secondaire sur la page"],
  ["mute", "card", 4.5, "texte secondaire sur carte"],
  ["g", "card", 4.5, "texte et lien vert sur carte"],
  ["g", "bg", 4.5, "texte et lien vert sur la page"],
  ["on-g", "g", 4.5, "texte de bouton principal"],
  ["ok-ink", "ok-bg", 4.5, "étiquette « bon »"],
  ["warn-ink", "warn-bg", 4.5, "étiquette « attention »"],
  ["bad-ink", "bad-bg", 4.5, "étiquette « critique »"],
  ["bad-ink", "card", 4.5, "message d'erreur sur carte"],
  ["blue", "card", 4.5, "lien bleu sur carte"],
  ["focus", "bg", 3, "anneau de focus"],
  ["focus", "card", 3, "anneau de focus sur carte"],
];

let failures = 0;
for (const [name, selector] of [
  ["clair", ":root"],
  ["sombre", ':root[data-theme="dark"]'],
]) {
  const tokens = block(selector);
  console.log(`\nThème ${name}`);
  for (const [fg, bg, min, usage] of PAIRS) {
    if (!tokens[fg] || !tokens[bg]) {
      console.log(`  ?    ${fg}/${bg} : jeton absent (${usage})`);
      continue;
    }
    const r = ratio(tokens[fg], tokens[bg]);
    const ok = r >= min;
    if (!ok) failures += 1;
    console.log(
      `  ${ok ? "ok  " : "ÉCHEC"} ${r.toFixed(2).padStart(5)} (min ${min}) ${fg} sur ${bg} — ${usage}`,
    );
  }
}
console.log(
  failures === 0 ? "\nTous les contrastes sont conformes." : `\n${failures} contraste(s) insuffisant(s).`,
);
process.exit(failures === 0 ? 0 : 1);
