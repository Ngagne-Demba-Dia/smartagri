// Produit les fichiers de travail pour la traduction humaine du wolof et du pulaar.
// Usage : node scripts/export-translations.mjs
// Sortie : messages/traduction/{wo,ff}.csv  (clé ; texte français ; traduction à remplir)
// wo.json et ff.json restent vides tant qu'une personne compétente n'a pas validé les traductions :
// l'application se replie alors sur le français (voir i18n/request.ts).
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const fr = JSON.parse(readFileSync(join(root, "messages", "fr.json"), "utf8"));

function flatten(node, prefix = "") {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === "object" && value !== null ? flatten(value, path) : [[path, String(value)]];
  });
}

const quote = (text) => `"${text.replaceAll('"', '""')}"`;
const rows = flatten(fr);
const outDir = join(root, "messages", "traduction");
mkdirSync(outDir, { recursive: true });

for (const locale of ["wo", "ff"]) {
  const lines = ["cle;francais;traduction", ...rows.map(([key, text]) => `${key};${quote(text)};`)];
  writeFileSync(join(outDir, `${locale}.csv`), `﻿${lines.join("\r\n")}\r\n`, "utf8");
}
console.log(`${rows.length} textes exportés vers messages/traduction/{wo,ff}.csv`);
