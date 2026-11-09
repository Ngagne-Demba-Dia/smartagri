#!/usr/bin/env node
/**
 * Contrôle des messages next-intl (npm run i18n:check).
 * - Toute clé statique utilisée dans le code (t("a.b")) existe dans messages/fr.json.
 * - Toute clé dynamique (t(`verdict.${x}`)) correspond à au moins une clé de fr.json.
 * - wo.json et ff.json ne contiennent que des clés connues de fr.json (le reste retombe sur le français),
 *   avec les mêmes variables {x} que le texte français.
 * Option --list : affiche les clés utilisées et les variables passées (aide à la rédaction).
 * Sortie 1 si une erreur est trouvée ; les clés inutilisées sont signalées sans faire échouer.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const SOURCE_DIRS = ["app", "components", "features", "hooks", "lib", "mocks", "services"];
const LOCALE_FILES = ["wo", "ff"];

function walk(dir) {
  let out = [];
  let entries = [];
  try {
    entries = readdirSync(dir);
  } catch {
    return out;
  }
  for (const name of entries) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out = out.concat(walk(path));
    else if (/\.(ts|tsx)$/.test(name) && !name.endsWith(".d.ts")) out.push(path);
  }
  return out;
}

function flatten(obj, prefix = "") {
  const out = new Map();
  for (const [key, value] of Object.entries(obj)) {
    if (key === "_meta") continue;
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object") for (const [k, v] of flatten(value, path)) out.set(k, v);
    else out.set(path, String(value));
  }
  return out;
}

/** Variables ICU de premier niveau : {count}, {name, plural, ...} → count, name. */
function placeholders(text) {
  const names = new Set();
  let depth = 0;
  let start = -1;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === "{") {
      if (depth === 0) start = i + 1;
      depth += 1;
    } else if (ch === "}") {
      depth -= 1;
      if (depth === 0 && start >= 0) {
        const name = text.slice(start, i).split(",")[0].trim();
        if (/^\w+$/.test(name)) names.add(name);
      }
    }
  }
  return [...names].sort().join(",");
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Déclarations de traducteurs d'un fichier, avec leur position : `const t = useTranslations("ns")` et les
 * paramètres typés `t: ReturnType<typeof useTranslations<"ns">>` (fonctions d'aide).
 */
function declarations(code) {
  const decl =
    /const\s+(\w+)\s*=\s*(?:await\s+)?(?:useTranslations|getTranslations)\(\s*(?:\{\s*(?:locale:\s*[\w.]+,\s*)?namespace:\s*)?(?:"([^"]*)")?/g;
  const param =
    /(\w+)\s*:\s*ReturnType<\s*typeof\s+(?:useTranslations|getTranslations)<\s*"([^"]*)"\s*>\s*>/g;
  const found = [];
  for (const m of code.matchAll(decl)) found.push({ name: m[1], ns: m[2] ?? "", at: m.index });
  for (const m of code.matchAll(param)) found.push({ name: m[1], ns: m[2], at: m.index });
  return found.sort((a, b) => a.at - b.at);
}

/**
 * Un appel est rattaché à la dernière déclaration du même nom qui le précède dans le fichier : plusieurs
 * composants d'un même fichier peuvent ainsi nommer `t` des traducteurs d'espaces différents.
 */
function scan() {
  const uses = [];
  for (const dir of SOURCE_DIRS) {
    for (const file of walk(join(ROOT, dir))) {
      const code = readFileSync(file, "utf8");
      const rel = relative(ROOT, file).replaceAll("\\", "/");
      const decls = declarations(code);
      for (const name of new Set(decls.map((d) => d.name))) {
        const own = decls.filter((d) => d.name === name);
        const call = new RegExp(
          `(?<![\\w.])${name}(?:\\.(?:rich|markup|raw|has))?\\(\\s*(?:"([^"]+)"|\`([^\`]+)\`)\\s*(,\\s*\\{([^}]*)\\})?`,
          "g",
        );
        for (const m of code.matchAll(call)) {
          const binding = own.filter((d) => d.at < m.index).at(-1);
          if (!binding) continue;
          const key = m[1] ?? m[2];
          const dynamic = m[2] !== undefined && m[2].includes("${");
          const full = binding.ns ? `${binding.ns}.${key}` : key;
          const params = (m[4] ?? "")
            .split(",")
            .map((p) => p.split(":")[0].trim())
            .filter((p) => /^\w+$/.test(p))
            .sort()
            .join(",");
          uses.push({ file: rel, key: full, dynamic, params });
        }
      }
    }
  }
  return uses;
}

function load(locale) {
  const path = join(ROOT, "messages", `${locale}.json`);
  return JSON.parse(readFileSync(path, "utf8"));
}

function main() {
  const uses = scan();
  if (process.argv.includes("--list")) {
    const seen = new Map();
    for (const u of uses)
      seen.set(u.key, `${u.key}${u.params ? `  {${u.params}}` : ""}${u.dynamic ? "  (dynamique)" : ""}`);
    for (const line of [...seen.values()].sort()) process.stdout.write(`${line}\n`);
    return 0;
  }
  const fr = flatten(load("fr"));
  const errors = [];
  const used = new Set();
  for (const u of uses) {
    if (u.dynamic) {
      const pattern = new RegExp(
        `^${u.key
          .split(/\$\{[^}]+\}/)
          .map(escapeRegex)
          .join("[\\w-]+")}$`,
      );
      const matches = [...fr.keys()].filter((k) => pattern.test(k));
      if (matches.length === 0) errors.push(`${u.file} : aucune clé ne correspond à ${u.key}`);
      for (const k of matches) used.add(k);
      continue;
    }
    if (fr.has(u.key)) used.add(u.key);
    else if ([...fr.keys()].some((k) => k.startsWith(`${u.key}.`))) used.add(u.key);
    else errors.push(`${u.file} : clé absente de fr.json : ${u.key}`);
  }
  for (const locale of LOCALE_FILES) {
    const messages = flatten(load(locale));
    for (const [key, text] of messages) {
      if (!fr.has(key)) errors.push(`${locale}.json : clé inconnue de fr.json : ${key}`);
      else if (placeholders(text) !== placeholders(fr.get(key))) {
        errors.push(`${locale}.json : variables différentes du français pour ${key}`);
      }
    }
  }
  const unused = [...fr.keys()].filter((k) => ![...used].some((u) => k === u || k.startsWith(`${u}.`)));
  for (const k of unused) process.stdout.write(`avertissement : clé inutilisée ${k}\n`);
  for (const e of errors) process.stderr.write(`erreur : ${e}\n`);
  process.stdout.write(
    `${uses.length} appels, ${fr.size} clés françaises, ${errors.length} erreur(s), ${unused.length} inutilisée(s).\n`,
  );
  return errors.length === 0 ? 0 : 1;
}

process.exit(main());
