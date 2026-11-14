import { expect, test, type Page } from "@playwright/test";

import { login, ROUTES } from "./helpers";

const LOADING_WAIT_MS = 30_000;

/** Contrôles structurels WCAG 2.1 AA vérifiables sans bibliothèque externe. */
async function structuralProblems(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const problems: string[] = [];
    const name = (el: Element): string =>
      (
        el.getAttribute("aria-label") ??
        document.getElementById(el.getAttribute("aria-labelledby") ?? "")?.textContent ??
        el.textContent ??
        ""
      ).trim();
    if (!document.documentElement.lang) problems.push("html sans attribut lang");
    for (const img of document.querySelectorAll("img:not([alt])"))
      problems.push(`img sans alt : ${img.outerHTML.slice(0, 80)}`);
    for (const el of document.querySelectorAll("button, a[href], [role=button], [role=tab]")) {
      if (!name(el) && !el.querySelector("img[alt]:not([alt=''])"))
        problems.push(`contrôle sans nom accessible : ${el.outerHTML.slice(0, 100)}`);
    }
    for (const el of document.querySelectorAll("input:not([type=hidden]), select, textarea")) {
      const id = el.getAttribute("id");
      const labelled =
        el.getAttribute("aria-label") ||
        el.getAttribute("aria-labelledby") ||
        el.closest("label") ||
        (id && document.querySelector(`label[for="${CSS.escape(id)}"]`));
      if (!labelled) problems.push(`champ sans étiquette : ${el.outerHTML.slice(0, 100)}`);
    }
    const ids = new Map<string, number>();
    for (const el of document.querySelectorAll("[id]")) ids.set(el.id, (ids.get(el.id) ?? 0) + 1);
    for (const [id, n] of ids) if (n > 1) problems.push(`id en double : ${id}`);
    const levels = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((h) => Number(h.tagName[1]));
    levels.reduce((prev, cur) => {
      if (cur - prev > 1) problems.push(`saut de niveau de titre : h${prev} puis h${cur}`);
      return cur;
    }, 1);
    return problems;
  });
}

test.describe("accessibilité", () => {
  test("structure accessible sur les 23 écrans (langue, noms, étiquettes, titres)", async ({ page }) => {
    test.setTimeout(900_000);
    await login(page);
    const all: string[] = [];
    for (const route of ROUTES) {
      await page.goto(`/fr/${route}`, { waitUntil: "networkidle" });
      await page
        .getByText(/^Chargement/)
        .first()
        .waitFor({ state: "hidden", timeout: LOADING_WAIT_MS });
      for (const p of await structuralProblems(page)) all.push(`/${route} : ${p}`);
    }
    expect(all, all.join("\n")).toEqual([]);
  });

  test("tout contrôle interactif atteint au clavier montre un indicateur de focus", async ({ page }) => {
    await login(page);
    await page.goto("/fr/tableau", { waitUntil: "networkidle" });
    const missing: string[] = [];
    for (let i = 0; i < 25; i += 1) {
      await page.keyboard.press("Tab");
      const visible = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        if (!el || el === document.body) return true;
        const s = getComputedStyle(el);
        const outline = s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0;
        return outline || s.boxShadow !== "none";
      });
      if (!visible)
        missing.push(await page.evaluate(() => document.activeElement?.outerHTML.slice(0, 90) ?? ""));
    }
    expect(missing, missing.join("\n")).toEqual([]);
  });

  test("dialogue mobile, formulaires, téléversement photo et assistant accessibles au clavier et aux lecteurs d'écran", async ({
    page,
  }) => {
    await login(page);

    // 1. Tiroir <dialog> mobile : ouverture, aria-label, fermeture par Échap
    await page.setViewportSize({ width: 375, height: 800 });
    await page.goto("/fr/tableau", { waitUntil: "networkidle" });
    const menuBtn = page.getByRole("button", { name: "Menu" });
    await expect(menuBtn).toBeVisible();
    await menuBtn.click();
    const dialog = page.getByRole("dialog", { name: "Menu" });
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();

    // Retour en taille bureau pour la suite
    await page.setViewportSize({ width: 1280, height: 800 });

    // 2. Formulaire de seuils sur Détail Parcelle : étiquettes et validation accessible
    await page.goto("/fr/parcelles/fld-ndiol-1", { waitUntil: "networkidle" });
    await page.getByText(/^Chargement/).first().waitFor({ state: "hidden", timeout: LOADING_WAIT_MS });
    await expect(page.getByLabel("Démarrage (%)")).toBeVisible();
    await expect(page.getByLabel("Arrêt (%)")).toBeVisible();

    // 3. Téléversement Maladies : champ relié à son aide par aria-describedby + conseil prise de vue
    await page.goto("/fr/maladies", { waitUntil: "networkidle" });
    await page.getByText(/^Chargement/).first().waitFor({ state: "hidden", timeout: LOADING_WAIT_MS });
    const fileInput = page.getByLabel("Photo de la plante");
    await expect(fileInput).toBeVisible();
    const describedBy = await fileInput.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    await expect(page.getByText(/Conseil prise de vue/)).toBeVisible();

    // 4. Assistant IA : suggestions rapides au clavier, compteur aria-describedby et journal role=log
    await page.goto("/fr/assistant", { waitUntil: "networkidle" });
    const suggestion = page.getByRole("button", { name: "Dois-je arroser demain ?" });
    await expect(suggestion).toBeVisible();
    await suggestion.focus();
    await page.keyboard.press("Enter");
    const questionInput = page.getByLabel("Votre question");
    await expect(questionInput).toHaveValue("Dois-je arroser demain ?");
    await expect(page.getByText("24 / 2000 caractères")).toBeVisible();
    await expect(page.getByRole("log", { name: "Conversation avec l’assistant" })).toBeVisible();
  });
});
