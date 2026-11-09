# 20. Frontend — version candidate (Release Candidate)

> **Confidentiel — réservé aux partenaires de travail.** Document local, à ne publier nulle part.
>
> Version 1, 09/11/2026. Périmètre : `plateforme/web/` uniquement. Aucun changement dans le backend, le doc 16 (baseline IA v1), les 18 contrats, `services/ai/`, les mocks, les hooks existants ni les routes existantes. Ce document clôt la mission commencée au doc 19 (audit).

## 1. Verdict

Le Frontend atteint le critère d'arrêt validé : **version candidate, sur données simulées**.

| Critère | État |
|---|---|
| 18 services sur 18 ont un écran | Oui (13 sur 18 au doc 19, 5 ajoutés : 2, 4, 10, 11, 15) |
| Aucun module « prévu » | Oui : les 13 modules sont complets (lecture seule pour Cultures, Campagnes, Rendement, Équipements) |
| `lint`, `typecheck`, `i18n:check`, `test`, `test:coverage`, `build` | Verts (§ 3) |
| Playwright en production (build puis `next start`) | 18 tests sur 18 réussis |
| Responsive 375 / 768 / 1280 / 1920 px | 23 écrans × 4 tailles : 0 débordement horizontal, 0 écran bloqué en chargement |
| Accessibilité WCAG 2.1 AA | Contrastes calculés conformes ; contrôles structurels et clavier réussis (§ 6) ; **pas d'audit par un outil dédié ni par un lecteur d'écran** (§ 8) |
| Aucune erreur de console bloquante | 0 erreur, 0 avertissement sur 23 écrans, en production (CSP comprise) |
| Aucun avertissement React | Les deux défauts trouvés sont corrigés et couverts par test (§ 5) |

« Candidate » veut dire : prête à être branchée sur le Backend. Cela ne veut pas dire validée sur de vraies données, de vrais appareils ni par de vrais utilisateurs.

## 2. Ce qui a été finalisé

1. **Cinq écrans manquants** : `/previsions` (service 2 `soil_forecast`), `/planning` (4 `irrigation_plan`), `/pieges` (10 `trap_counts`), `/vegetation` (11 `vegetation`), `/marches` (15 `price_forecast`). Les hooks, mocks et schémas existaient déjà : seule la couche d'affichage a été ajoutée.
2. **Quatre modules à moitié finis, terminés** : Cultures (cycle et étapes), Campagnes (avancement calculé à partir des dates, jamais inventé), Rendement (prévision avec intervalle p10–p90, marquée expérimentale), Équipements. Les coquilles `features/shells/` sont supprimées.
3. **Composants de données** : `KpiCard`, `Meter`, `Sparkline`, `ConfidenceBadge`, `AiCard`, `Segmented`, `Steps`, `StatusTag`, `DataTable`, `Chart` (SVG, sans dépendance, avec tableau de valeurs), `Skeleton`, `EmptyState`, `Hero`, `TimeAgo`, `TranslationBanner`.
4. **Habillage des écrans existants** avec ces composants : tableau de bord, exploitations, parcelles, carte, météo, irrigation, fertilisation, risques, maladies, kit, alertes, recommandations.
5. **Police Inter auto-hébergée** et photo du prototype (validées par le propriétaire).
6. **Repli wolof et pulaar** : voir § 7.

Règles d'honnêteté conservées et protégées par des tests :

- une confiance non calibrée n'est jamais affichée en pourcentage (« probabilité non calibrée ») ;
- un résultat périmé n'est jamais présenté comme frais ;
- `fallback_step > 0` affiche « Valeur de secours » ;
- le service 8 s'abstient sous 0,7 ;
- une provenance absente affiche « Provenance non communiquée par l’API. ».

## 3. Chiffres

| Mesure | Valeur |
|---|---|
| Routes applicatives | 23 écrans + détail de parcelle + connexion ; 6 routes d'API (BFF) |
| Modules | 13 sur 13 complets |
| Composants partagés (`components/`) | 29 + dossier `chart/` |
| Fichiers de fonctionnalités (`features/`) | 39 fichiers, 25 dossiers |
| Tests unitaires et composants (vitest) | **30 fichiers, 610 tests, tous verts** (521 au doc 19) |
| Tests navigateur (Playwright) | **18 tests, tous verts** : `auth` 5, `parcours` 6, `qualite` 4, `accessibilite` 2, `visual-audit` 1 |
| Couverture (`lib/`, `services/`, `mocks/`) | lignes **99,18 %**, instructions 97,8 %, fonctions 98,88 %, branches 89,16 % (seuil visé : 80 %) |
| Messages français | 832 clés ; `i18n:check` : 0 erreur, 35 avertissements « clé inutilisée » (clés construites dynamiquement, non suivies par l'outil) |
| Plus gros fichier source | 434 lignes (`lib/types.ts`) ; tous sous le plafond de 800 |
| JS partagé au premier chargement | 103 kB ; 131 à 185 kB par écran ; 305 à 308 kB pour les écrans à graphique ou carte (`marches`, `meteo`, `pieges`, `previsions`, `rendement`, `vegetation`) |

La couverture ne mesure pas les composants React (`vitest.config` limite le périmètre) : ils sont couverts par les tests de composants et par Playwright, sans pourcentage.

## 4. Tests

- **Vitest** : contrats, mocks, lib pures, et tests de composants sous jsdom avec Testing Library (`tests/components/`) : écrans d'IA (irrigation, fertilisation, risques), modules, services, hydratation.
- **`auth.spec.ts`** : redirection avec `next=`, mauvais mot de passe, champs vides, connexion puis déconnexion et accès fermé, connexion au clavier seul.
- **`parcours.spec.ts`** : tableau de bord vers une parcelle ; irrigation et provenance ; recommandations ; maladies (photo, verdict) ; assistant (question, réponse, nouvelle conversation) ; rapports (plage de dates invalide refusée).
- **`qualite.spec.ts`** : console propre sur 23 écrans ; lien d'évitement ; un seul `main` et un seul `h1` ; pas de défilement horizontal à 375 px ; repli wolof sans clé brute visible.
- **`accessibilite.spec.ts`** : voir § 6.
- **`visual-audit.spec.ts`** : 23 écrans × 4 tailles, captures dans `web/audit-shots/` (dossier local, non livré).

`npm run test:e2e` lance le serveur de développement avec les mocks ; `E2E_PROD=1 npm run test:e2e` lance le build de production (`next build` d'abord). Le port utilisé est 3100.

## 5. Défauts réels trouvés par les tests navigateur, et corrigés

| Défaut | Cause | Correction | Test |
|---|---|---|---|
| Erreur React #418 (hydratation) sur `/assistant`, en production seulement | `VoiceInput` testait la capacité d'enregistrement du navigateur pendant le rendu : serveur et client rendaient deux textes différents | indicateur « hydraté » (`useSyncExternalStore`) ; rien n'est rendu côté serveur | `tests/components/hydration.test.tsx` |
| Avertissement « Cannot update a component (`SyncBanner`) while rendering a different component » | l'abonnement au cache de requêtes appelait `setState` pendant le rendu d'un autre composant | mise à jour différée par `queueMicrotask`, annulée au démontage | `hydration.test.tsx` |
| Saut de niveau de titre (h1 puis h3) sur Cultures et Campagnes | cartes titrées en `h3` | `h2` | `accessibilite.spec.ts` |
| En-tête à 768 px : « Se déconnecter » sur deux lignes, puis 5 px de débordement | libellé non protégé contre le retour à la ligne ; pastille de rôle trop large | `whitespace-nowrap` ; pastille de rôle affichée dès 1024 px | `visual-audit.spec.ts` |

Les erreurs « Applying inline style violates » du serveur de développement viennent de la surcouche de Next.js et n'existent pas en production : le test de console les ignore en développement seulement.

## 6. Responsive et accessibilité

**Responsive.** Mesuré sur le build de production, 23 écrans à 375 × 800, 768 × 1024, 1280 × 800 et 1920 × 1080 : aucun débordement horizontal. Cibles tactiles de 44 px (`min-h-touch`). Captures examinées à la main : tableau de bord (1920), irrigation (375), rendement (768).

**WCAG 2.1 AA, ce qui est vérifié :**

- contrastes (`npm run contrast`, thèmes clair et sombre) : tous au-dessus de 4,5 pour le texte et de 3 pour l'anneau de focus (le plus faible : 4,26 pour le focus en clair, 4,60 pour le lien bleu) ;
- langue du document, aucune image sans `alt`, aucun bouton ni lien sans nom accessible, aucun champ sans étiquette, aucun identifiant en double, aucun saut de niveau de titre, sur les 23 écrans ;
- lien « Aller au contenu » en première position au clavier, un seul `main`, un seul `h1`, navigation présente ;
- indicateur de focus visible sur les 25 premiers arrêts de tabulation du tableau de bord ;
- connexion possible au clavier seul ;
- chaque graphique a un tableau de valeurs, l'état d'un résultat ne repose jamais sur la couleur seule (icône et libellé) ;
- thème sombre : couleurs propres, pas une simple inversion.

## 7. Internationalisation

- **Français** : 832 clés, source de vérité.
- **Wolof et pulaar** : `wo.json` et `ff.json` restent vides, par décision du propriétaire. L'interface se replie sur le français et affiche un bandeau d'information ; aucune clé brute n'est visible (test). **Aucune traduction n'a été inventée.**
- **Prêt pour la traduction humaine** : `node scripts/export-translations.mjs` produit `web/messages/traduction/wo.csv` et `ff.csv` (colonnes : clé, texte français, traduction à remplir ; UTF-8 avec BOM, ouvrable dans un tableur). Le retour des traductions se fait en remplissant `wo.json` / `ff.json` avec les mêmes clés ; `i18n:check` signale les clés manquantes ou inconnues.

## 8. Dette restante, dite sans détour

1. **Traductions wolof et pulaar** : en attente d'une validation humaine (décision, pas oubli).
2. **Audit d'accessibilité par outil dédié** (par exemple axe-core) : non fait, car il demande une nouvelle dépendance que le propriétaire n'a pas validée. Les contrôles du § 6 sont faits à la main dans Playwright et couvrent la structure, pas tout (par exemple l'ordre de lecture d'un graphique, ou le rôle d'un composant ARIA complexe).
3. **Lecteur d'écran réel** (NVDA, VoiceOver, TalkBack) et **appareils réels** : non testés. La validation visuelle (étape 10) s'est faite dans Chromium, au moteur Playwright, à 4 tailles, avec captures examinées sur un échantillon de trois écrans ; pas dans Firefox, Safari ni sur téléphone.
4. **Données simulées uniquement.** Le Frontend n'a jamais été branché sur le Backend : formats de réponses, latences, erreurs réseau réelles et authentification réelle restent à valider à l'intégration.
5. **Modules en lecture seule** : Cultures, Campagnes, Rendement, Équipements n'ont aucune route d'écriture.
6. **Composants hors couverture chiffrée** : voir § 3.
7. **Avertissement de démarrage** : `next start` signale que `output: "standalone"` demande plutôt `node .next/standalone/server.js`. Sans effet pour les tests ; à traiter au déploiement (hors périmètre).
8. **35 clés signalées « inutilisées »** par `i18n:check` : clés dynamiques (par exemple `crops.filter.*`). À nettoyer ou à déclarer à l'outil, sans urgence.
9. **Poids** : les écrans à graphique ou à carte chargent environ 305 kB de JavaScript ; acceptable pour l'usage prévu, à surveiller en connexion lente.

## 8 bis. Avertissement pratique

Les builds et les lancements de Playwright partagent le dossier `.next` avec le serveur de développement du propriétaire (port 3000) : **ce serveur doit être relancé** (`npm run dev:mock`). Les tests Playwright utilisent le port 3100.

## 9. Fichiers ajoutés ou modifiés depuis le doc 19 (résumé)

- Écrans et vues : `features/{soil-forecast,irrigation-plan,traps,vegetation,markets}/`, `features/{crops,campaigns,yield,equipment}/`, pages sous `app/[locale]/(app)/`.
- Composants : voir § 2. Corrections : `features/assistant/VoiceInput.tsx`, `components/SyncBanner.tsx`, `components/AppShell.tsx`, titres de `CropsView` et `CampaignsView`.
- Messages : `messages/fr.json` (+180 clés), `messages/traduction/{wo,ff}.csv` (générés).
- Outils : `scripts/start-mock.mjs`, `scripts/export-translations.mjs`, `playwright.config.ts`.
- Tests : `tests/components/{ai-screens,module-screens,service-screens,hydration}.test.tsx`, `tests/modules-lib.test.ts`, `e2e/*.spec.ts`.

## 10. Commandes de vérification

```text
cd plateforme/web
npm run lint          # eslint --max-warnings 0
npm run typecheck
npm run i18n:check
npm run test
npm run test:coverage
npm run contrast
npm run build
E2E_PROD=1 npm run test:e2e     # après npm run build
```
