#!/usr/bin/env node
/**
 * Lance le serveur de PRODUCTION (next start, après `next build`) en mode simulé (AGRI_MOCK=1), sans latence.
 * Sert aux parcours Playwright contre le build réel. Port : variable PORT (3000 par défaut).
 */
import { spawn } from "node:child_process";

const port = process.env.PORT ?? "3000";
const child = spawn("npx", ["next", "start", "--port", port], {
  stdio: "inherit",
  shell: true,
  env: { ...process.env, AGRI_MOCK: "1", AGRI_MOCK_LATENCY: process.env.AGRI_MOCK_LATENCY ?? "0" },
});
child.on("exit", (code) => process.exit(code ?? 0));
