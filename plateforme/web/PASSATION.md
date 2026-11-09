# PASSATION — Frontend SmartAgri92 (Release Candidate GELÉE)

_Dernière mise à jour : 2026-11-09, après la passe visuelle « Premium AgriTech ». **Frontend gelé en Release Candidate** : aucune nouvelle fonctionnalité avant l'ouverture du Sprint D (Backend & Intégration) ; améliorations futures = backlog v1.1 (`docs/21_cloture_frontend_rc.md` § 6)._

## 1. État d’avancement

| Vague | État |
|---|---|
| 0–1 Audit, outillage (Playwright, jsdom, Testing Library, Inter) | Fait (`docs/19_audit_frontend_et_refonte.md`) |
| 2 Composants de données | Fait |
| 3 Habillage des écrans existants | Fait (avec tests de composants des écrans d'IA) |
| 4 Cinq services sans écran + quatre modules complets | Fait : 18/18 services ont un écran, 13/13 modules complets |
| 5 Responsive, WCAG AA, i18n | Fait : 0 débordement à 375/768/1280/1920 ; contrastes conformes ; contrôles structurels et clavier ; wo/ff = repli français + CSV de traduction |
| 6 Playwright, RTL, production, React, CSP, couverture | Fait : voir § 2 |
| 7 Passe visuelle « Premium AgriTech » | Fait : verre, profondeur, animations, cartes de parcelles, météo immersive, conseiller agronomique, illustrations |
| Rapport final | Fait : `docs/20_frontend_release_candidate.md` puis clôture `docs/21_cloture_frontend_rc.md` |

## 2. Dernière vérification (build de production)

- `eslint --max-warnings 0` propre ; `tsc --noEmit` propre ; `i18n:check` 0 erreur (41 « inutilisée » : clés dynamiques).
- vitest : 30 fichiers / 610 tests verts ; couverture lignes 99,00 %, branches 88,93 %.
- `next build` vert ; Playwright avec `E2E_PROD=1` : 18/18 (auth 5, parcours 6, qualité 4, accessibilité 2, audit visuel 1). Une régression (h1→h3 sur /meteo) a été détectée puis corrigée ; accessibilité, qualité et parcours rejoués : 12/12.
- Audit visuel : 23 écrans × 4 tailles, 0 débordement, 0 écran bloqué, 0 erreur de console ; aucune erreur ni avertissement de console, CSP comprise.
- `npm run contrast` : tous les contrastes conformes (clair et sombre).

## 3. Fichiers modifiés ou créés depuis la 4b

- Vues habillées (Vague 3) : Dashboard, FarmsList, FieldsList, AlertsLog, WeatherView, IrrigationView, FertilizationView, PestRiskView, DiagnosisView, KitView, FieldMap, RecommendationsList ; `messages/fr.json` (nouvelles clés).
- Corrections de défauts réels : `features/assistant/VoiceInput.tsx` (hydratation, React #418), `components/SyncBanner.tsx` (setState pendant un rendu), `components/AppShell.tsx` (en-tête à 768 px), titres h2 dans `features/crops/CropsView.tsx` et `features/campaigns/CampaignsView.tsx`.
- `lib/modules.ts` : commentaire du champ `complete` mis à jour.
- Outils : `scripts/start-mock.mjs`, `scripts/export-translations.mjs`, `playwright.config.ts` (`E2E_PROD=1`).
- Tests : `tests/components/{ai-screens,hydration}.test.tsx`, `e2e/{auth,parcours,qualite,accessibilite}.spec.ts` (+ `visual-audit`).
- Générés : `messages/traduction/{wo,ff}.csv` ; captures locales dans `web/audit-shots/`.
- Doc : `docs/20_frontend_release_candidate.md`, `docs/21_cloture_frontend_rc.md`.
- Passe visuelle : `app/globals.css`, `components/{Icon,Illustrations,WeatherHero,Meter}.tsx`, `features/fields/FieldLiveCard.tsx`, `features/weather/WeatherView.tsx`, `features/dashboard/Dashboard.tsx`, `features/recommendations/{RecommendationCards,RecommendationsList}.tsx`, `messages/fr.json` (15 clés).

## 4. Problèmes rencontrés

- Bash à plusieurs heredocs : échoue (« unexpected EOF ») ; un fichier par appel Write.
- `next build` et `next dev` écrasent `.next` : un lancement de Playwright pendant un build échoue avec « Cannot find module ./3897.js ». Toujours builder, puis tester.
- `sr-only sm:not-sr-only` remet `white-space: normal` : mettre `sm:whitespace-nowrap` sur le même `span`.
- **Le serveur de développement de l’utilisateur (port 3000) est à relancer** : `.next` a été écrasé par les builds. Les tests utilisent le port 3100.

## 5. Décisions prises

- Ordre : 2 → 4 → 3 → 5 → 6.
- Modules Cultures, Campagnes, Rendement, Équipements : lecture seule.
- Wolof/Pulaar : repli français ; `wo.json` et `ff.json` restent `{}` jusqu’à validation humaine ; CSV d’aide à la traduction générés.
- Pas d’axe-core ni d’autre dépendance non validée : contrôles d’accessibilité écrits dans Playwright.
- Aucune modification de Doc 16, des 18 contrats, de `services/ai/`, des mocks, des hooks, des routes existantes.
- Confidentialité : rien publié ni envoyé ; jamais `octopus-ml`.

## 6. Prochaine tâche exacte

Frontend gelé. Prochaine étape : ouverture du **Sprint D (Backend & Intégration)**. Pendant le gel, seules les corrections de régression et les ajustements imposés par l'intégration sont admis. Suites, par décision du propriétaire :

1. Faire traduire `messages/traduction/wo.csv` et `ff.csv`, puis remplir `wo.json` / `ff.json` et lancer `npm run i18n:check`.
2. Brancher le Frontend sur le Backend (Sprint D) puis rejouer `E2E_PROD=1 npm run test:e2e`.
3. Audit d’accessibilité avec un outil dédié (nouvelle dépendance à valider) et essai au lecteur d’écran et sur appareils réels.
4. Nettoyer les 35 clés « inutilisées » signalées par `i18n:check`.
5. Backlog v1.1 (hors gel) : photos et illustrations supplémentaires, modules en écriture, relecture visuelle humaine après la passe Premium — détail dans `docs/21_cloture_frontend_rc.md` § 6.
