import { expect, type Page } from "@playwright/test";

export const DEMO_USER = "agriculteur@demo.sn";
export const DEMO_PASSWORD = "demo";

/** Modules de l'application (segments d'URL sous /fr/). */
export const ROUTES = [
  "tableau",
  "exploitations",
  "parcelles",
  "carte",
  "meteo",
  "irrigation",
  "fertilisation",
  "risques",
  "recommandations",
  "assistant",
  "maladies",
  "kit",
  "alertes",
  "rapports",
  "equipements",
  "cultures",
  "campagnes",
  "rendement",
  "previsions",
  "planning",
  "pieges",
  "vegetation",
  "marches",
] as const;

/** Tailles de validation : mobile, tablette, portable, bureau. */
export const VIEWPORTS = [
  { name: "mobile", width: 375, height: 800 },
  { name: "tablette", width: 768, height: 1024 },
  { name: "portable", width: 1280, height: 800 },
  { name: "bureau", width: 1920, height: 1080 },
] as const;

/** Connexion avec le compte de démonstration (mode simulé). */
export async function login(page: Page, user = DEMO_USER): Promise<void> {
  await page.goto("/fr/login", { waitUntil: "networkidle" });
  const idInput = page.getByLabel("Identifiant");
  const pwInput = page.getByLabel("Mot de passe");
  const submitBtn = page.getByRole("button", { name: /se connecter/i });
  await idInput.fill(user);
  await pwInput.fill(DEMO_PASSWORD);
  await submitBtn.click();
  try {
    await expect(page).toHaveURL(/\/fr\/tableau/, { timeout: 15_000 });
  } catch {
    await idInput.fill(user);
    await pwInput.fill(DEMO_PASSWORD);
    await submitBtn.click();
    await expect(page, "connexion refusée ou page lente").toHaveURL(/\/fr\/tableau/, { timeout: 90_000 });
  }
}
