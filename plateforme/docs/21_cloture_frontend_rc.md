# 21. Clôture du Frontend — Release Candidate gelée

_Date : 2026-11-09. Document confidentiel (partenaires uniquement). Complète le doc 20._

## 1. Décision

Le Frontend est **gelé en Release Candidate**. Aucune nouvelle fonctionnalité Frontend n'est développée avant l'ouverture officielle du **Sprint D (Backend & Intégration)**. Les améliorations futures vont au backlog v1.1 (§ 6).

Seules exceptions admises pendant le gel : correction d'une régression, ou ajustement imposé par l'intégration Backend (contrat, authentification).

## 2. Ce qui a été fait dans la dernière passe (« Premium AgriTech »)

Passe **uniquement visuelle**. Routes, contrats, services, hooks, API, Doc 16 et tests existants : inchangés.

| Axe | Réalisation |
|---|---|
| Fond agricole | Flou du verre réduit (16→10 px, 22→15 px, 7 px sur mobile) ; photo plus saturée, voile allégé, vignette |
| Profondeur | Ombres multicouches (clair et sombre), soulèvement des cartes au survol |
| Verre | Reflet spéculaire, double liseré, saturation 1,6 |
| Micro-animations | Anneau et jauge qui se dessinent, reflet sur les boutons, orbe IA qui flotte, point « en direct » ; `prefers-reduced-motion` respecté |
| Parcelles | Cartes visuelles : bandeau photo, pastille de culture illustrée, statut, liseré de verdict |
| Météo | `WeatherHero` : ciel illustré et animé (sec / faible pluie / pluie), semaine en tuiles ; même style sur le tableau de bord |
| Recommandations IA | Conseiller agronomique : avatar, bannière « Mon conseil », bulle, frise Constat → Dose → À savoir, mention de prudence |
| Illustrations | `components/Illustrations.tsx` (cultures, sillons, ciels, avatar) ; 7 icônes ajoutées |

Fichiers touchés : `app/globals.css`, `components/{Icon,Illustrations,WeatherHero,Meter}.tsx`, `features/fields/FieldLiveCard.tsx`, `features/weather/WeatherView.tsx`, `features/dashboard/Dashboard.tsx`, `features/recommendations/{RecommendationCards,RecommendationsList}.tsx`, `messages/fr.json` (15 clés : `weather.hero.*`, `recommendations.advisor.*`).

## 3. Vérification sur la version de production

| Contrôle | Résultat |
|---|---|
| `eslint --max-warnings 0` | propre |
| `tsc --noEmit` | propre |
| `i18n:check` | 0 erreur (860 clés, 41 « inutilisées » : clés dynamiques et réserve) |
| `npm run contrast` | tous conformes (clair et sombre) |
| vitest | 30 fichiers, **610 / 610** |
| Couverture | lignes 99,00 %, instructions 97,61 %, branches 88,93 %, fonctions 98,57 % |
| `next build` | vert, 23 écrans + 6 routes API |
| Playwright (`E2E_PROD=1`, port 3100) | **18 / 18** après correction (voir § 4) |
| Audit visuel | 23 écrans × 4 tailles : 0 débordement, 0 écran bloqué, 0 erreur de console |

## 4. Régression détectée et corrigée

- **Détection** : la 1re exécution Playwright donnait 17/18. Test en échec : `accessibilite › structure accessible sur les 23 écrans`, message « /meteo : saut de niveau de titre : h1 puis h3 ».
- **Cause** : le titre « Les prochains jours » du nouveau `WeatherHero` était un `h3` placé directement sous le `h1` de la page.
- **Correction** : `h3` → `h2` dans `components/WeatherHero.tsx` (une ligne).
- **Revalidation** : build refait, puis accessibilité (2), qualité (4) et parcours (6) : 12/12 verts. Les 6 autres tests (auth 5, audit visuel 1) n'avaient pas échoué et le correctif ne touche aucun de leurs écrans.

## 5. Points d'attention

- Le serveur de développement de l'utilisateur (port 3000) est à relancer : `.next` a été écrasé par les builds. Les tests utilisent le port 3100.
- `next start` signale que `output: standalone` demande `node .next/standalone/server.js` ; sans effet sur les tests (mode simulé), à traiter au déploiement du Sprint D.
- Le rendu visuel a été contrôlé par les captures de l'audit (`web/audit-shots/`, local) et par les tests automatiques ; il n'a pas fait l'objet d'une relecture humaine écran par écran après cette passe.
- Wolof et Pulaar : toujours repli français (`wo.json` / `ff.json` = `{}`).

## 6. Backlog v1.1 (hors gel)

1. Traduction wolof / pulaar (CSV déjà générés) puis `i18n:check`.
2. Photos agricoles supplémentaires : le projet n'en a qu'une, réutilisée en variantes.
3. Illustrations dédiées (EmptyState, cartes KPI, bandeau) et vraies photos de parcelles issues du Backend.
4. Audit d'accessibilité avec outil dédié, lecteur d'écran et appareils réels.
5. Nettoyage des clés i18n inutilisées.
6. Modules Cultures, Campagnes, Rendement, Équipements : passage de la lecture seule à l'écriture, selon les endpoints Backend.

## 7. Entrée du Sprint D

Brancher le Frontend sur le Backend, puis rejouer `E2E_PROD=1 npm run test:e2e`. Aucun contrat des 18 services ni le Doc 16 ne doit changer sans décision du propriétaire.
