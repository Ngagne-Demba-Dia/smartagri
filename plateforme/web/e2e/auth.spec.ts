import { expect, test } from "@playwright/test";

import { DEMO_PASSWORD, DEMO_USER, login } from "./helpers";

test.describe("authentification", () => {
  test("redirige vers la connexion sans session et garde la page demandée", async ({ page }) => {
    await page.goto("/fr/irrigation");
    await expect(page).toHaveURL(/\/fr\/login\?next=%2Firrigation/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("refuse un mauvais mot de passe avec un message clair", async ({ page }) => {
    await page.goto("/fr/login");
    await page.getByLabel("Identifiant").fill(DEMO_USER);
    await page.getByLabel("Mot de passe").fill("incorrect");
    await page.getByRole("button", { name: "Se connecter" }).click();
    await expect(page.locator("p[role=alert]")).toContainText("Identifiant ou mot de passe incorrect.");
    await expect(page).toHaveURL(/\/fr\/login/);
  });

  test("demande les deux champs avant d'appeler le serveur", async ({ page }) => {
    await page.goto("/fr/login");
    await page.getByRole("button", { name: "Se connecter" }).click();
    await expect(page.locator("p[role=alert]")).toContainText(
      "Saisissez votre identifiant et votre mot de passe.",
    );
  });

  test("connecte puis déconnecte, et ferme l'accès aux pages", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
    await page.getByRole("button", { name: "Se déconnecter" }).click();
    await expect(page).toHaveURL(/\/fr\/login/);
    await page.goto("/fr/tableau");
    await expect(page).toHaveURL(/\/fr\/login/);
  });

  test("connexion au clavier seulement", async ({ page }) => {
    await page.goto("/fr/login");
    await page.getByLabel("Identifiant").focus();
    await page.keyboard.type(DEMO_USER);
    await page.keyboard.press("Tab");
    await page.keyboard.type(DEMO_PASSWORD);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/fr\/tableau/, { timeout: 90_000 });
  });
});
