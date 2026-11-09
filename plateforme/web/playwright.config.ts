import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

/** Parcours de bout en bout contre le serveur de développement en mode simulé (AGRI_MOCK=1). */
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    locale: "fr-FR",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: process.env.E2E_PROD === "1" ? "node scripts/start-mock.mjs" : "node scripts/dev-mock.mjs",
    url: `http://localhost:${PORT}/fr/login`,
    env: { PORT: String(PORT), AGRI_MOCK: "1" },
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
