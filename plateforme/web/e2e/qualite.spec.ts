import { expect, test, type ConsoleMessage } from "@playwright/test";

import { login, ROUTES } from "./helpers";

const LOADING_WAIT_MS = 30_000;

/** Bruit connu et sans effet sur l'application : outils de développement uniquement. */
const IGNORED = [/Download the React DevTools/i];

/** Le serveur de développement de Next.js injecte son propre style en ligne (absent du build de production). */
const DEV_ONLY = process.env.E2E_PROD === "1" ? [] : [/Applying inline style violates/];

const isProblem = (m: ConsoleMessage): boolean =>
  (m.type() === "error" || m.type() === "warning") &&
  ![...IGNORED, ...DEV_ONLY].some((re) => re.test(m.text()));

test.describe("qualité", () => {
  test("aucune erreur ni avertissement de console sur les 23 écrans (dont React et CSP)", async ({
    page,
  }) => {
    test.setTimeout(900_000);
    const problems: string[] = [];
    page.on("console", (m) => {
      if (isProblem(m))
        problems.push(`${new URL(page.url()).pathname} [${m.type()}] ${m.text().slice(0, 300)}`);
    });
    page.on("pageerror", (e) => problems.push(`${new URL(page.url()).pathname} [exception] ${e.message}`));
    await login(page);
    for (const route of ROUTES) {
      await page.goto(`/fr/${route}`, { waitUntil: "networkidle" });
      await page
        .getByText(/^Chargement/)
        .first()
        .waitFor({ state: "hidden", timeout: LOADING_WAIT_MS });
    }
    expect(problems, problems.join("\n")).toEqual([]);
  });

  test("lien d'évitement et repères de page au clavier", async ({ page }) => {
    await login(page);
    await page.goto("/fr/tableau");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Aller au contenu" });
    await expect(skip).toBeFocused();
    await expect(page.getByRole("main")).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByRole("navigation").first()).toBeVisible();
  });

  test("aucun défilement horizontal à 375 px sur les écrans de données", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await login(page);
    for (const route of ["tableau", "irrigation", "meteo", "equipements", "rendement", "marches"]) {
      await page.goto(`/fr/${route}`, { waitUntil: "networkidle" });
      const wide = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(wide, `/${route}`).toBeLessThanOrEqual(0);
    }
  });

  test("la langue wolof se replie sur le français sans clé manquante visible", async ({ page }) => {
    await login(page);
    await page.goto("/wo/tableau");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const raw = await page.getByRole("main").innerText();
    expect(raw).not.toMatch(/\b[a-z]+\.[a-zA-Z]+\.[a-zA-Z]+\b/);
  });
});
