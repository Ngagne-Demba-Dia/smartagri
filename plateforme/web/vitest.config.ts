import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./", import.meta.url)) },
  },
  // Les composants sont testés en JSX « automatic » (Next compile le sien avec `jsx: preserve`).
  esbuild: { jsx: "automatic" },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
    setupFiles: ["tests/setup-dom.ts"],
    coverage: {
      provider: "v8",
      include: ["lib/**/*.ts", "services/**/*.ts", "mocks/**/*.ts"],
      exclude: ["lib/server/**", "lib/types.ts"],
    },
  },
});
