import { expect, test, type Page } from "@playwright/test";

import { login } from "./helpers";

/** 1×1 PNG : suffit pour traverser le contrôle de format et la réduction côté navigateur. */
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);

async function open(page: Page, route: string, title: string): Promise<void> {
  await page.goto(`/fr/${route}`);
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await expect(page.getByText(/^Chargement/).first()).toBeHidden({ timeout: 30_000 });
}

test.describe("parcours principaux", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("tableau de bord : indicateurs, puis navigation vers une parcelle", async ({ page }) => {
    await open(page, "tableau", "Tableau de bord");
    await expect(page.getByRole("term").first()).toBeVisible();
    await page.getByRole("link", { name: "Parcelles" }).first().click();
    await expect(page).toHaveURL(/\/fr\/parcelles/);
    await expect(page.getByRole("heading", { level: 1, name: "Parcelles" })).toBeVisible();
    const firstField = page.locator('main a[href*="/parcelles/"]').first();
    if (await firstField.count()) {
      await firstField.click();
      await expect(page).toHaveURL(/\/fr\/parcelles\/.+/);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }
  });

  test("irrigation : besoin en eau avec sa provenance", async ({ page }) => {
    await open(page, "irrigation", "Irrigation");
    const card = page.getByRole("region", { name: "Besoin en eau à 24 h" });
    await expect(card).toBeVisible();
    await card.getByText("Provenance").click();
    await expect(card.getByText(/Modèle|modèle/).first()).toBeVisible();
  });

  test("recommandations : liste de conseils et retour de l'utilisateur", async ({ page }) => {
    await open(page, "recommandations", "Recommandations");
    await expect(page.getByText("Avez-vous suivi cette recommandation ?").first()).toBeVisible();
  });

  test("maladies : envoi d'une photo et verdict avec avertissement", async ({ page }) => {
    await open(page, "maladies", "Maladies");
    await page.getByLabel("Photo de la plante").setInputFiles({
      name: "feuille.png",
      mimeType: "image/png",
      buffer: TINY_PNG,
    });
    await page.getByRole("button", { name: "Analyser la photo" }).click();
    await expect(
      page.getByText(/Plante saine|Maladie probable|Suspect|Incertain, faites vérifier/).first(),
    ).toBeVisible({ timeout: 30_000 });
  });

  test("assistant : question, réponse et nouvelle conversation", async ({ page }) => {
    await open(page, "assistant", "Assistant IA");
    await page.getByLabel("Votre question").fill("Dois-je arroser demain ?");
    await page.getByRole("button", { name: "Envoyer" }).click();
    const log = page.getByRole("log", { name: "Conversation avec l’assistant" });
    await expect(log).toContainText("Dois-je arroser demain ?");
    await expect(log.getByText("Assistant", { exact: true }).first()).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Nouvelle conversation" }).click();
    await expect(
      page.getByText("Posez une question sur vos parcelles, l’irrigation ou la météo."),
    ).toBeVisible();
  });

  test("rapports : indicateurs sur une période et plage invalide refusée", async ({ page }) => {
    await page.getByRole("button", { name: "Se déconnecter" }).click();
    await login(page, "cooperative@demo.sn");
    await open(page, "rapports", "Rapports");
    await expect(page.getByText("Mesures reçues").first()).toBeVisible();
    await page.getByLabel("Du", { exact: true }).fill("2099-12-31");
    await page.getByLabel("Au", { exact: true }).fill("2000-01-01");
    await expect(page.getByText("La date de début doit précéder la date de fin.")).toBeVisible();
  });
});
