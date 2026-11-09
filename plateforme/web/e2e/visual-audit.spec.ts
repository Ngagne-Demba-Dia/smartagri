import { mkdirSync } from "node:fs";

import { test } from "@playwright/test";

import { login, ROUTES, VIEWPORTS } from "./helpers";

const LOADING_WAIT_MS = 30_000;

/** Regroupe les erreurs de console identiques (hash et nonce retirés) pour un rapport lisible. */
function summarize(errors: string[]): string {
  const counts = new Map<string, number>();
  for (const e of errors) {
    const key = e
      .replace(/'(sha256|nonce)-[^']*'/g, "'…'")
      .replace(/nonce-[^\s']*/g, "nonce-…")
      .slice(0, 220);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return (
    [...counts]
      .sort((a, b) => b[1] - a[1])
      .map(([k, n]) => `${n} × ${k}`)
      .join("\n") || "aucune"
  );
}

/**
 * Audit visuel (étape 10) : une capture par écran et par taille dans audit-shots/,
 * et un rapport des débordements horizontaux, des écrans restés en chargement et des erreurs de console.
 * Lancé à la demande : `npx playwright test visual-audit`.
 */
test.describe("audit visuel", () => {
  test("captures et débordements", async ({ page }) => {
    test.setTimeout(1_500_000);
    const consoleErrors: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error") consoleErrors.push(`${new URL(page.url()).pathname} ${m.text()}`);
    });
    await login(page);
    const overflows: string[] = [];
    const stuck: string[] = [];
    for (const vp of VIEWPORTS) {
      mkdirSync(`audit-shots/${vp.name}`, { recursive: true });
      await page.setViewportSize({ width: vp.width, height: vp.height });
      for (const route of ROUTES) {
        await page.goto(`/fr/${route}`, { waitUntil: "networkidle" });
        try {
          await page
            .getByText(/^Chargement/)
            .first()
            .waitFor({ state: "hidden", timeout: LOADING_WAIT_MS });
        } catch {
          stuck.push(`${vp.name} /${route}`);
        }
        const wide = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (wide > 0) overflows.push(`${vp.name} /${route} : +${wide}px`);
        await page.screenshot({ path: `audit-shots/${vp.name}/${route}.png`, fullPage: true });
      }
    }
    console.log(`Débordements horizontaux (${overflows.length}) :\n${overflows.join("\n") || "aucun"}`);
    console.log(`Restés en chargement (${stuck.length}) :\n${stuck.join("\n") || "aucun"}`);
    console.log(`Erreurs de console (${consoleErrors.length}) :\n${summarize(consoleErrors)}`);
  });
});
