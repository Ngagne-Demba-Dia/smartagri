# SmartAgri92 — plateforme web

Confidentiel — réservé aux partenaires de travail.

Tableau de bord SmartAgri92 : Next.js 15 (App Router), React 19, TypeScript strict. Le navigateur ne parle qu'au BFF Next.js (`/api/*`), qui garde la session dans des cookies `httpOnly` et relaie les appels vers l'API. Les 18 services d'IA du doc 16 § 9 sont lus par des contrats zod ; tant que leurs routes ne sont pas livrées, ils sont simulés.

Référence : [docs/17_frontend_v0_1.md](../docs/17_frontend_v0_1.md) (écrans, contrats, simulations, retrait d'une simulation). Conventions communes : [CONVENTIONS.md](../CONVENTIONS.md).

## Installation

Node `>=22.12 <25` (développé sous Node 24.14).

```bash
npm install        # en intégration continue : npm ci
```

Les versions sont épinglées sans plage dans `package.json` ; `package-lock.json` fait foi.

### Remplacements dans `package.json` (`overrides`)

| Remplacement | Raison |
|---|---|
| `rollup` → `npm:@rollup/wasm-node@4.68.0` | Le contrôle d'applications de Windows bloque le binaire natif de Rollup chargé par Vite (donc par Vitest). La version WebAssembly a la même API, un peu plus lente. |
| `@typescript-eslint/eslint-plugin` et `@typescript-eslint/parser` → `8.71.2` | La version tirée par `eslint-config-next` faisait planter ESLint 9.39. |
| `postcss` → `$postcss` | Une seule version de PostCSS, celle déclarée. |

À revoir à chaque montée de version de Next, de Vite ou d'ESLint.

## Scripts

| Commande | Effet |
|---|---|
| `npm run dev` | Serveur de développement sur `http://localhost:3000` |
| `npm run build` puis `npm start` | Construction et serveur de production (port 3000) |
| `npm run lint` | ESLint, aucun avertissement toléré |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest (environnement Node, sans DOM) |
| `npm run test:coverage` | Tests et couverture de `lib/`, `services/` et `mocks/` |
| `npm run i18n:check` | Clés de traduction. Seul le français est rempli ; `wo.json` et `ff.json` sont vides (wolof et pulaar prévus) |

Avant de livrer : `npm run lint`, `npm run typecheck`, `npm run i18n:check`, `npm run test:coverage` et `npm run build` doivent réussir.

## Mode simulé

Avec `AGRI_MOCK=1`, le BFF ne fait aucun appel réseau : la session et toutes les routes sont servies en mémoire par les gestionnaires de `mocks/`. Aucune autre valeur n'active ce mode (`true` ne l'active pas).

```powershell
# PowerShell
$env:AGRI_MOCK = "1"; npm run dev
```

```bash
# bash
AGRI_MOCK=1 npm run dev
```

Variables facultatives, lues au démarrage du serveur :

| Variable | Valeurs | Effet |
|---|---|---|
| `AGRI_MOCK_SCENARIO` | `nominal`, `stale`, `fallback`, `abstention`, `error_503`, `empty` | Scénario global initial ; `nominal` si absent ou inconnu |
| `AGRI_MOCK_LATENCY` | nombre ≥ 0, plafonné à 10 | Facteur appliqué aux latences simulées ; `0` supprime l'attente, `1` par défaut |

Exemple, tous les services en repli et sans attente :

```bash
AGRI_MOCK=1 AGRI_MOCK_SCENARIO=fallback AGRI_MOCK_LATENCY=0 npm run dev
```

**Comptes de démonstration**, mot de passe `demo` (aussi proposés sur la page de connexion) :

| Compte | Rôle | Organisation |
|---|---|---|
| `agriculteur@demo.sn` | agriculteur | Exploitation démo — Ndiol |
| `cooperative@demo.sn` | responsable de coopérative | Coopérative démo — Niayes |
| `agronome@demo.sn` | agronome | Coopérative démo — Niayes |
| `admin@demo.sn` | administrateur | les deux |

**Pilotage des scénarios.** Une fois connecté, le bandeau « Mode simulé » en haut de chaque écran ouvre, par « Régler la simulation », un panneau qui change le scénario global ou celui d'un service, et remet tout à zéro. Il appelle la route `/api/dev/mock`, qui n'existe qu'en mode simulé :

- `GET` : scénario global, surcharges par service, facteur de latence ;
- `POST {"scenario": "...", "service": "..."}` : change un scénario (`"scenario": null` avec un service retire sa surcharge) ;
- `DELETE` : nominal partout, seuils, acquittements et retours remis à zéro.

Le détail des scénarios et des réponses simulées est au § 7 du doc 17.

## Mode réel

Sans `AGRI_MOCK=1`, le BFF relaie vers l'API. `API_BASE_URL` est alors obligatoire ; il n'est jamais exposé au navigateur.

```powershell
# PowerShell
$env:API_BASE_URL = "http://localhost:8000"; npm run dev
```

```bash
# bash
API_BASE_URL=http://localhost:8000 npm run dev
```

En Kubernetes : `http://api.smartagri92.svc.cluster.local:8000`. Une session ne mélange jamais routes simulées et routes réelles : quand une simulation est retirée, son écran se développe contre l'API d'intégration (doc 17 § 3).

## Arborescence

| Dossier | Contenu |
|---|---|
| `app/` | Pages (`[locale]/(app)/…`), routes du BFF (`api/v1/[...path]`, `api/auth/*`, `api/dev/mock`, `api/health`) |
| `features/` | Écrans par module ; aucun `fetch` dans un composant |
| `components/` | Composants partagés (provenance, états de requête, navigation) |
| `services/ai/` | Hooks et appels des 18 services, clés de cache |
| `hooks/` | Hooks des routes du socle (exploitations, parcelles, kits, seuils) |
| `lib/contracts/` | Enveloppe, provenance, registre des 18 services, schémas zod |
| `lib/server/` | Code serveur du BFF (accès à l'API, session) |
| `mocks/` | Simulations : gestionnaires, données de démonstration, scénarios |
| `messages/` | Traductions : `fr` rempli ; `wo` et `ff` vides, l'interface s'affiche alors en français |
| `tests/` | Tests Vitest |
