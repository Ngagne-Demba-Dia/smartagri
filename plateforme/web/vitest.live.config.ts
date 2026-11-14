import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

/**
 * Tests de contrat live (Sprint D1) : appellent l'API réelle (`npm run test:live`), jamais lancés par
 * `npm test`. La pile est démarrée à part : `python -m scripts.live_stack --stack-file ../web/.live-stack.json`
 * (dossier backend/), ou n'importe quelle API dont l'URL et les identifiants sont dans LIVE_STACK_FILE.
 */
export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./", import.meta.url)) } },
  test: {
    environment: "node",
    include: ["tests/live/**/*.live.ts"],
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
});
