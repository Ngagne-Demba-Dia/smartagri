#!/usr/bin/env node
/**
 * Lance le serveur de développement en mode simulé (AGRI_MOCK=1), sous Windows comme ailleurs.
 * Port : variable PORT (3000 par défaut).
 */
import { spawn } from "node:child_process";

const port = process.env.PORT ?? "3000";
const child = spawn("npx", ["next", "dev", "--port", port], {
  stdio: "inherit",
  shell: true,
  env: { ...process.env, AGRI_MOCK: "1" },
});
child.on("exit", (code) => process.exit(code ?? 0));
