import { expect, test } from "@playwright/test";

import { login } from "./helpers";

/** 1×1 PNG valide pour tester la réduction Canvas et l'envoi sur Chromium, Firefox et WebKit (Safari). */
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);

test.describe("validation multi-navigateur (Phase E2)", () => {
  test("cookies httpOnly, thème sombre (localStorage), responsive, animations, Leaflet, upload image et micro", async ({
    page,
    context,
  }) => {
    test.setTimeout(180_000);

    // 1. Authentification, cookies httpOnly (sa_at) et politique localStorage (aucun jeton stocké dans localStorage, doc 10 §7)
    await login(page);
    const cookies = await context.cookies();
    const accessCookie = cookies.find((c) => c.name === "sa_at");
    expect(accessCookie).toBeDefined();
    expect(accessCookie?.httpOnly).toBe(true);

    const storageOk = await page.evaluate(() => {
      /* eslint-disable no-restricted-properties */
      const hasToken = Object.keys(window.localStorage).some((k) => /token|auth|sa_at|sa_rt/i.test(k));
      window.localStorage.setItem("sa_browser_check", "ok");
      const readBack = window.localStorage.getItem("sa_browser_check");
      window.localStorage.removeItem("sa_browser_check");
      /* eslint-enable no-restricted-properties */
      return !hasToken && readBack === "ok";
    });
    expect(storageOk).toBe(true);

    // 2. Thème sombre (attribut data-theme="dark" + cookie sa-theme=dark sans flash SSR)
    await page.goto("/fr/tableau", { waitUntil: "networkidle" });
    await expect(page.getByText(/^Chargement/).first()).toBeHidden({ timeout: 30_000 });
    const themeBtn = page.getByRole("button", { name: /Passer au thème sombre/i });
    await themeBtn.click();
    const dataTheme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    const themeCookie = (await context.cookies()).find((c) => c.name === "sa-theme");
    expect(dataTheme).toBe("dark");
    expect(themeCookie?.value).toBe("dark");

    // 3. Animations CSS et respect de prefers-reduced-motion
    await page.emulateMedia({ reducedMotion: "reduce" });
    const animDuration = await page.evaluate(() => {
      const el = document.querySelector(".reveal");
      return el ? parseFloat(getComputedStyle(el).animationDuration) : 0;
    });
    expect(animDuration).toBeLessThanOrEqual(0.001);
    await page.emulateMedia({ reducedMotion: "no-preference" });

    // 4. Carte Leaflet : rendu des polygones SVG, contrôles de zoom et légende
    await page.goto("/fr/carte", { waitUntil: "networkidle" });
    await expect(page.getByText(/^Chargement/).first()).toBeHidden({ timeout: 30_000 });
    await expect(page.locator(".leaflet-container")).toBeVisible();
    await expect(page.locator(".leaflet-container svg path").first()).toBeVisible();
    await page.getByRole("radio", { name: "NDVI (vigueur)" }).click();
    await expect(page.getByRole("radio", { name: "NDVI (vigueur)" })).toBeChecked();

    // 5. Upload image + Canvas prepareImage + diagnostic Maladies
    await page.goto("/fr/maladies", { waitUntil: "networkidle" });
    await expect(page.getByText(/^Chargement/).first()).toBeHidden({ timeout: 30_000 });
    await page.getByLabel("Photo de la plante").setInputFiles({
      name: "feuille.png",
      mimeType: "image/png",
      buffer: TINY_PNG,
    });
    await expect(page.getByAltText("Aperçu de la photo qui sera envoyée")).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: "Analyser la photo" }).click();
    await expect(
      page.getByText(/Plante saine|Maladie probable|Suspect|Incertain, faites vérifier/).first(),
    ).toBeVisible({ timeout: 30_000 });

    // 6. Assistant IA + Microphone (bouton de dictée ou message d'indisponibilité propre selon les capacités MediaRecorder du moteur)
    await page.goto("/fr/assistant", { waitUntil: "networkidle" });
    const voiceBtn = page.getByRole("button", { name: "Dicter ma question" });
    const voiceUnsupported = page.getByText("La dictée n’est pas disponible sur cet appareil.");
    await expect(voiceBtn.or(voiceUnsupported)).toBeVisible({ timeout: 15_000 });

    // 7. Responsive 375 px : barre de navigation mobile, absence de débordement horizontal
    await page.setViewportSize({ width: 375, height: 800 });
    await page.goto("/fr/irrigation", { waitUntil: "networkidle" });
    await expect(page.getByText(/^Chargement/).first()).toBeHidden({ timeout: 30_000 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await expect(page.getByText(/Repère terrain : 1 mm d’eau équivaut à 1 L\/m²/)).toBeVisible();
  });
});
