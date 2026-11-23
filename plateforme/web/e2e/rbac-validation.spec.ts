import { mkdirSync, writeFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { login } from "./helpers";

const SHOT_DIR = "audit-shots/rbac";

interface RoleTestSpec {
  id: string;
  email: string;
  roleLabel: string;
  expectedEyebrow: string;
  expectedDashboardMarkers: string[];
  absentDashboardMarkers: string[];
  allowedSampleRoutes: { slug: string; heading: string }[];
  forbiddenRoutes: string[];
  expectedNavCount: number;
}

const ROLE_SPECS: readonly RoleTestSpec[] = [
  {
    id: "farmer",
    email: "agriculteur@demo.sn",
    roleLabel: "Rôle : Agriculteur",
    expectedEyebrow: "Espace Agriculteur · Pilotage terrain quotidien",
    expectedDashboardMarkers: [
      "Mon plan d’action du jour",
      "Conseils & alertes",
      "Qualité eau d’arrosage",
      "Cours Oignon (Dakar)",
    ],
    absentDashboardMarkers: [
      "Supervision multi-organisations & règles d’alertes",
      "Matrice de diagnostic agronomique par parcelle",
      "Périmètres de la coopérative",
    ],
    allowedSampleRoutes: [
      { slug: "parcelles", heading: "Parcelles" },
      { slug: "irrigation", heading: "Irrigation" },
      { slug: "meteo", heading: "Météo" },
      { slug: "communaute", heading: "Communauté des agriculteurs" },
      { slug: "carte", heading: "Carte" },
    ],
    forbiddenRoutes: ["exploitations", "rapports", "kit", "vegetation", "previsions", "equipements"],
    expectedNavCount: 18,
  },
  {
    id: "coop_manager",
    email: "cooperative@demo.sn",
    roleLabel: "Rôle : Gestionnaire de coopérative",
    expectedEyebrow: "Espace Coopérative · Gestion mutualisée, eau & marchés",
    expectedDashboardMarkers: [
      "Synthèse de la Coopérative aujourd’hui",
      "Périmètres de la Coopérative",
      "Classement des membres / exploitations",
      "Marchés de gros, Tendances & Recommandations de commercialisation",
      "Campagne active, Progression & Étapes restantes",
      "Surface exploitée",
      "Production prévisionnelle",
      "Eau consommée",
      "Eau économisée (30 j)",
      "Prix moyen marché",
      "Risques critiques",
    ],
    absentDashboardMarkers: [
      "Mon plan d’action du jour",
      "Matrice de diagnostic agronomique par parcelle",
      "Santé de la plateforme & Supervision multi-organisations",
    ],
    allowedSampleRoutes: [
      { slug: "exploitations", heading: "Exploitations" },
      { slug: "rapports", heading: "Rapports" },
      { slug: "equipements", heading: "Équipements" },
      { slug: "campagnes", heading: "Campagnes" },
      { slug: "marches", heading: "Prix du marché" },
    ],
    forbiddenRoutes: ["kit", "vegetation", "previsions"],
    expectedNavCount: 21,
  },
  {
    id: "agronomist",
    email: "agronome@demo.sn",
    roleLabel: "Rôle : Agronome",
    expectedEyebrow: "Cockpit Agronome · Vigie phytosanitaire, NDVI, NPK & eau",
    expectedDashboardMarkers: [
      "Matrice de diagnostic agronomique par parcelle",
      "Parcelles Prioritaires (Classement agronomique)",
      "Pourquoi cette parcelle est critique ?",
      "SoilNowcast",
      "Rain Intelligence",
      "Anomaly Intelligence",
      "Cockpit IA Prédictif",
      "Humidité prévue J+1 · J+2 · J+3 (SoilNowcast)",
      "NDVI & vigueur",
      "Adoption des conseils IA",
      "Diagnostics foliaires (30 j)",
      "Eau (pH / CE)",
    ],
    absentDashboardMarkers: [
      "Mon plan d’action du jour",
      "Périmètres de la coopérative",
      "Santé de la plateforme & Supervision multi-organisations",
    ],
    allowedSampleRoutes: [
      { slug: "vegetation", heading: "Végétation" },
      { slug: "previsions", heading: "Humidité prévue" },
      { slug: "kit", heading: "Paramètres du kit" },
      { slug: "fertilisation", heading: "Fertilisation" },
      { slug: "maladies", heading: "Maladies" },
    ],
    forbiddenRoutes: ["equipements"],
    expectedNavCount: 23,
  },
  {
    id: "admin",
    email: "admin@demo.sn",
    roleLabel: "Rôle : Administrateur",
    expectedEyebrow: "Supervision Administrateur · Multi-organisations & Flotte IoT",
    expectedDashboardMarkers: [
      "Santé de la plateforme & Supervision multi-organisations",
      "Supervision de la Flotte IoT",
      "Répartition des alertes par règle",
      "État des services IA",
      "SoilNowcast",
      "Rain Intelligence",
      "Sources et synchronisation des seuils relais",
      "Organisations supervisées",
      "Kits en ligne",
      "Mesures 24h",
      "Synchronisations en attente",
    ],
    absentDashboardMarkers: [
      "Mon plan d’action du jour",
      "Périmètres de la coopérative",
      "Matrice de diagnostic agronomique par parcelle",
      "Communauté & alertes entre agriculteurs",
    ],
    allowedSampleRoutes: [
      { slug: "exploitations", heading: "Exploitations" },
      { slug: "rapports", heading: "Rapports" },
      { slug: "kit", heading: "Paramètres du kit" },
      { slug: "vegetation", heading: "Végétation" },
      { slug: "previsions", heading: "Humidité prévue" },
      { slug: "equipements", heading: "Équipements" },
    ],
    forbiddenRoutes: [],
    expectedNavCount: 24,
  },
];

async function waitPageLoaded(page: Page): Promise<void> {
  try {
    await page.getByText(/^Chargement/).first().waitFor({ state: "hidden", timeout: 25_000 });
  } catch {
    // Pas d'indicateur de chargement restant
  }
}

test.describe("MISSION FRONT-RBAC-03 — Validation fonctionnelle et visuelle des 4 rôles", () => {
  test.beforeAll(() => {
    mkdirSync(SHOT_DIR, { recursive: true });
  });

  for (const spec of ROLE_SPECS) {
    test(`Validation complète [${spec.id}] (${spec.email}) : connexion, sidebar, dashboard, accès URL direct, desktop & mobile`, async ({
      page,
    }) => {
      test.setTimeout(240_000);

      // 1. Desktop (1280×800) — Connexion & vérification du rôle dans l'en-tête
      await page.setViewportSize({ width: 1280, height: 800 });
      await login(page, spec.email);
      await waitPageLoaded(page);
      await expect(page.getByText(spec.roleLabel)).toBeVisible();

      // 2. Dashboard Desktop — Vérification de l'unicité du dashboard (eyebrow, KPIs, widgets présents/absents)
      await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
      await expect(page.getByText(spec.expectedEyebrow)).toBeVisible();
      for (const marker of spec.expectedDashboardMarkers) {
        await expect(page.getByText(marker).first(), `Widget/KPI attendu pour ${spec.id} : ${marker}`).toBeVisible();
      }
      for (const absent of spec.absentDashboardMarkers) {
        await expect(page.getByText(absent), `Widget interdit pour ${spec.id} : ${absent}`).toHaveCount(0);
      }

      // 2b. Vérifications P0 (FRONTEND_PRO_REVIEW.md) :
      // - Aucun doublon de KPI (<dt>) sur le dashboard (4 KPIs pour farmer/coop/agronomist, 6 KPIs pour admin)
      const kpiLists = page.locator("main dl").filter({ has: page.locator("div.card") });
      await expect(kpiLists, `Une seule rangée de KPIs attendue pour ${spec.id}`).toHaveCount(1);
      const kpiTerms = await kpiLists.first().locator("dt").allInnerTexts();
      const trimmedTerms = kpiTerms.map((t) => t.trim()).filter(Boolean);
      const expectedKpiCount = spec.id === "admin" || spec.id === "coop_manager" ? 6 : 4;
      expect(trimmedTerms.length, `Nombre de KPIs attendu (${expectedKpiCount}) pour ${spec.id}`).toBe(expectedKpiCount);
      expect(
        new Set(trimmedTerms).size,
        `Doublon de KPI détecté pour ${spec.id} : ${trimmedTerms.join(", ")}`,
      ).toBe(trimmedTerms.length);

      // - Aucune valeur KPI vide « — »
      const kpiValues = await kpiLists.first().locator("dd").allInnerTexts();
      for (const val of kpiValues) {
        expect(val.trim(), `KPI vide '—' interdit pour ${spec.id}`).not.toBe("—");
      }

      // - Aucune contradiction entre l'alerte critique et la synthèse IA
      const hasCriticalBanner = (await page.getByText(/alerte critique ouverte|alertes critiques ouvertes/).count()) > 0;
      if (hasCriticalBanner) {
        await expect(
          page.getByText("Tout est sous contrôle : aucune parcelle ne demande d’eau pour l’instant."),
          `Contradiction synthèse IA vs alerte critique pour ${spec.id}`,
        ).toHaveCount(0);
      }

      // - Absence totale de jargon technique brut sur le dashboard
      for (const jargon of ["field_boundary v1", "Non communiquée", "soil_dry", "device_offline", "fertilizer_low", "sensor_fault"]) {
        await expect(
          page.getByText(jargon, { exact: false }),
          `Jargon technique '${jargon}' interdit sur le dashboard ${spec.id}`,
        ).toHaveCount(0);
      }

      // Capture Desktop Dashboard
      await page.screenshot({
        path: `${SHOT_DIR}/${spec.id}-desktop-dashboard.png`,
        fullPage: true,
      });

      // 3. Navigation Sidebar Desktop — Vérification des liens visibles et de l'absence des routes interdites
      const desktopSidebarLinks = page.locator("aside nav a[href]");
      await expect(desktopSidebarLinks).toHaveCount(spec.expectedNavCount);
      const desktopHrefs = await desktopSidebarLinks.evaluateAll((els) =>
        els.map((el) => el.getAttribute("href") ?? ""),
      );
      const desktopLabels = await desktopSidebarLinks.evaluateAll((els) =>
        els.map((el) => (el.textContent ?? "").trim()),
      );

      for (const forbidden of spec.forbiddenRoutes) {
        expect(
          desktopHrefs,
          `La route interdite /fr/${forbidden} ne doit pas apparaître dans la sidebar de ${spec.id}`,
        ).not.toContain(`/fr/${forbidden}`);
      }

      // 4. Mobile (375×800) — Dashboard, absence de débordement horizontal et Tiroir Menu <dialog>
      await page.setViewportSize({ width: 375, height: 800 });
      await page.waitForTimeout(250);
      const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(mobileOverflow, `Débordement horizontal mobile sur dashboard ${spec.id}`).toBeLessThanOrEqual(0);

      await page.screenshot({
        path: `${SHOT_DIR}/${spec.id}-mobile-dashboard.png`,
        fullPage: true,
      });

      const menuBtn = page.getByRole("button", { name: "Menu" });
      await expect(menuBtn).toBeVisible();
      await menuBtn.click();
      const dialog = page.getByRole("dialog", { name: "Menu" });
      await expect(dialog).toBeVisible();

      const mobileDialogLinks = dialog.locator("nav a[href]");
      await expect(mobileDialogLinks).toHaveCount(spec.expectedNavCount);

      await page.screenshot({
        path: `${SHOT_DIR}/${spec.id}-mobile-sidebar.png`,
      });
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();

      // 5. Retour Desktop — Test des routes autorisées (navigation réelle)
      await page.setViewportSize({ width: 1280, height: 800 });
      for (const route of spec.allowedSampleRoutes) {
        await page.goto(`/fr/${route.slug}`, { waitUntil: "networkidle" });
        await waitPageLoaded(page);
        await expect(page.locator('[data-testid="rbac-forbidden"]')).toHaveCount(0);
        await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();
      }

      // 6. Test d'accès URL direct aux routes INTERDITES (doivent toutes être bloquées)
      for (let i = 0; i < spec.forbiddenRoutes.length; i += 1) {
        const forbidden = spec.forbiddenRoutes[i]!;
        await page.goto(`/fr/${forbidden}`, { waitUntil: "networkidle" });
        await waitPageLoaded(page);
        const guard = page.locator('[data-testid="rbac-forbidden"]');
        await expect(
          guard,
          `L'accès direct à /fr/${forbidden} doit être bloqué pour ${spec.id}`,
        ).toBeVisible();
        await expect(
          page.getByRole("heading", { level: 1, name: "Accès réservé à un autre profil" }),
        ).toBeVisible();

        if (i === 0) {
          await page.screenshot({
            path: `${SHOT_DIR}/${spec.id}-blocked-${forbidden}.png`,
          });
        }
      }

      // 7. Contrôles de permissions fines spécifiques au rôle
      if (spec.id === "agronomist") {
        // L'agronome accède aux parcelles en lecture seule (pas de formulaire de modification des seuils)
        await page.goto("/fr/parcelles/fld-mboro-1", { waitUntil: "networkidle" });
        await waitPageLoaded(page);
        await expect(page.getByLabel("Démarrage (%)")).toHaveCount(0);

        // L'agronome voit les recommandations mais sans les boutons de retour producteur
        await page.goto("/fr/recommandations", { waitUntil: "networkidle" });
        await waitPageLoaded(page);
        await expect(page.getByText("Avez-vous suivi cette recommandation ?")).toHaveCount(0);
      }

      if (spec.id === "farmer") {
        // L'agriculteur ne peut pas accéder à une parcelle d'une autre organisation (Mboro -> 404/introuvable)
        await page.goto("/fr/parcelles/fld-mboro-1", { waitUntil: "networkidle" });
        await waitPageLoaded(page);
        await expect(page.getByLabel("Démarrage (%)")).toHaveCount(0);

        // Sur sa propre parcelle (Ndiol 1), l'agriculteur dispose du formulaire d'édition des seuils
        await page.goto("/fr/parcelles/fld-ndiol-1", { waitUntil: "networkidle" });
        await waitPageLoaded(page);
        await expect(page.getByLabel("Démarrage (%)")).toBeVisible();
      }

      // Enregistre un résumé JSON factuel du test pour le rapport RBAC_VISUAL_VALIDATION.md
      writeFileSync(
        `${SHOT_DIR}/${spec.id}-report.json`,
        JSON.stringify(
          {
            role: spec.id,
            email: spec.email,
            roleLabel: spec.roleLabel,
            eyebrow: spec.expectedEyebrow,
            navCount: desktopHrefs.length,
            visibleHrefs: desktopHrefs,
            visibleLabels: desktopLabels,
            forbiddenBlocked: spec.forbiddenRoutes.map((r) => `/fr/${r}`),
            mobileOverflowPx: mobileOverflow,
          },
          null,
          2,
        ),
        "utf-8",
      );
    });
  }
});
