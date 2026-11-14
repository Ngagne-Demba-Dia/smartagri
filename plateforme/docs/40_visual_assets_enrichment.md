# 40 — Enrichissement de l'Identité Visuelle (`plateforme/web`)

**Date** : 14 novembre 2026  
**Périmètre** : `plateforme/web` — Groupes A (photographies de domaine WebP), B (visuels pédagogiques et terrain SVG in-card) et C (espèces maraîchères additionnelles dans `CropArt`)  
**Statut** : ✅ **INTÉGRÉ & VALIDÉ (`20/20` Playwright E2E, `630/630` Vitest, `0` débordement responsive, WCAG AA `14/14`)**

---

## 1. Respect des contraintes d'architecture

| Contrainte | Vérification | Statut |
|---|---|---|
| Aucune modification des routes (`app/[locale]/**`) | Aucune route ajoutée, renommée ou supprimée | ✅ |
| Aucune modification des contrats (`lib/contracts/*.ts`) | `0` fichier modifié dans `lib/contracts/` | ✅ |
| Aucune modification des services (`services/**`) | `0` fichier modifié dans `services/` | ✅ |
| Aucune modification des hooks (`hooks/**`) | `0` fichier modifié dans `hooks/` | ✅ |
| Aucune modification du Doc 16 (`16_architecture_octopus.md`) | Fichier intact | ✅ |
| Aucune nouvelle dépendance lourde (`package.json`) | `0` dépendance npm ajoutée | ✅ |
| Photos réelles libres de droits compatibles usage commercial | Domaine public (USDA / NRCS) et Creative Commons (`CC BY-SA 4.0` / `CC BY-SA 2.0`) avec attribution complète | ✅ |
| Format WebP entre **45 Ko et 60 Ko** par image | Toutes les photos pèsent entre **49,4 Ko et 54,7 Ko** (`1280×855`) | ✅ |
| Contraste WCAG AA conservé | Voile sombre de lisibilité renforcé (`rgba(15, 29, 18, 0.50 → 0.86)`) + `npm run contrast` `14/14` paires conformes | ✅ |

---

## 2. Groupe A — Photographies réelles par domaine métier (WebP `1280×855`, 45–60 Ko)

Avant cette intervention, une seule photographie (`public/img/champ-hero.webp`, **53,6 Ko**) était réutilisée sur l'ensemble de l'application via `photoForScene()`. Désormais, chaque famille fonctionnelle dispose de sa propre photographie agricole réelle, servie localement depuis `plateforme/web/public/img/` (compatible CSP `img-src 'self' data: blob:` et mode hors-ligne PWA) et chargée en `loading="lazy" decoding="async"` sur les bandeaux internes.

| Fichier WebP | Scène (`Scene`) | Dimensions | Poids exact | Source & Auteur (Wikimedia Commons) | Licence (Usage commercial OK) | Écrans concernés |
|---|---|---:|---:|---|---|---|
| [champ-hero.webp](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/public/img/champ-hero.webp) *(existant conservé)* | `login`, `dashboard`, `assistant` | `1280×855` | **53,6 Ko** (`54 862` o) | Champ maraîcher irrigué au soleil levant (photographie existante du projet) | Libre d'utilisation (asset initial Smart Agri) | `/fr/connexion`, `/fr/tableau`, `/fr/recommandations`, `/fr/assistant` |
| [parcelles-niayes.webp](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/public/img/parcelles-niayes.webp) | `parcelles` | `1280×855` | **53,9 Ko** (`55 194` o) | `File:Champs maraîchage au Lac Mbawane.jpg` — Maraîchage réel au Lac Mbawane (zone des Niayes, Sénégal) | **CC BY-SA 4.0** | `/fr/parcelles`, `/fr/parcelles/[id]`, `/fr/exploitations`, `/fr/campagnes`, `/fr/carte`, `/fr/fertilisation`, `/fr/vegetation`, `/fr/cultures` |
| [irrigation-goutte.webp](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/public/img/irrigation-goutte.webp) | `irrigation` | `1280×855` | **49,8 Ko** (`50 962` o) | `File:20130920-OC-LSC-0516 (10548031236).jpg` — USDA / Lance Cheung (goutte-à-goutte au pied d'un rang maraîcher sur sol humide) | **Domaine public** (US Gov / USDA) | `/fr/irrigation`, `/fr/meteo`, `/fr/previsions`, `/fr/planning` |
| [phyto-feuille.webp](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/public/img/phyto-feuille.webp) | `maladies` | `1280×855` | **54,1 Ko** (`55 416` o) | `File:Mr. Stripey Heirloom Tomato leaf.jpg` — Feuillage de tomate maraîchère en macro | **CC BY-SA 2.0** | `/fr/maladies`, `/fr/risques`, `/fr/pieges` |
| [kit-terrain.webp](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/public/img/kit-terrain.webp) | `kit` | `1280×855` | **54,7 Ko** (`55 972` o) | `File:Drought Mitigation - Reiter Berry Farms - Wireless Irrigation monitoring Network (20150827-NRCS-LSC-0258).jpg` — USDA NRCS / Lance Cheung (station de télémesure solaire en plein champ) | **Domaine public** (US Gov / USDA NRCS) | `/fr/kit`, `/fr/equipements`, `/fr/alertes` |
| [recolte-marche.webp](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/public/img/recolte-marche.webp) | `marches` | `1280×855` | **49,4 Ko** (`50 580` o) | `File:Bulk red onions and potatoes ready for delivery... (20150916-OSEC-LSC-0015).jpg` — USDA / Lance Cheung (récolte d'oignons rouges et pommes de terre en caisses/sacs) | **Domaine public** (US Gov / USDA) | `/fr/marches`, `/fr/rendement`, `/fr/rapports` |

### Détail technique d'intégration (Groupe A)
- **[lib/scene.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/scene.ts)** : centralise le type `Scene` (`"login" | "dashboard" | "parcelles" | "irrigation" | "maladies" | "kit" | "marches" | "assistant"`), la table de routage `SCENE_BY_SLUG` et la fonction `photoForScene(scene)`.
- **[components/Scene.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Scene.tsx)** : utilise `photoForScene(scene)` et adapte `loading="eager" fetchPriority="high"` uniquement sur l'écran de connexion, tout en appliquant `loading="lazy" decoding="async"` sur les bandeaux internes.
- **[components/ModuleShell.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/ModuleShell.tsx)** : résout automatiquement la scène métier de chaque route via `sceneForSlug(slug)` lorsque la prop `scene` n'est pas forcée explicitement.
- **[app/globals.css](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/app/globals.css)** : applique un traitement colorimétrique unifié (`saturate(1.06) contrast(1.03)`) et un cadrage `object-position` adapté à chaque sujet photographique (`parcelles`, `irrigation`, `maladies`, `kit`, `marches`) avec un dégradé de lisibilité garantissant un ratio de contraste supérieur à `7:1` pour les titres en blanc.

---

## 3. Groupe B — Visuels pédagogiques et terrain in-card (SVG inline `0 Ko` réseau)

Trois illustrations vectorielles métier ont été ajoutées dans [components/Illustrations.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Illustrations.tsx) pour guider l'agriculteur dans ses gestes de terrain :

| Composant | Écran & Fichier d'intégration | Emplacement | Rôle & Impact UX |
|---|---|---|---|
| `PhotoFramingGuide` | `/fr/maladies` — [DiagnosisView.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/diagnosis/DiagnosisView.tsx) | Sous la zone de dépôt photo (affiché uniquement tant qu'aucune photo n'est sélectionnée) | **Guide de prise de vue en 3 vignettes** : Compare visuellement *« 1 feuille nette plein cadre »* (recommandé, coche verte) face à *« Éviter : plant trop loin »* et *« Éviter : contre-jour ou ombre »*. Réduit les photos floues ou mal cadrées avant l'analyse phytosanitaire. |
| `StickyTrapArt` | `/fr/pieges` — [TrapsView.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/traps/TrapsView.tsx) | En-tête de chaque carte de relevé de piège chromatique (`56×56 px`) | **Plaque engluée jaune quadrillée** : Illustre concrètement le piège chromatique suspendu avec grille de comptage et spécimens capturés. Permet de distinguer immédiatement l'écran `/fr/pieges` des jauges de `/fr/risques`. |
| `KitMastDiagram` | `/fr/kit` — [KitHealth.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/kit/KitHealth.tsx) | Bandeau d'état matériel en haut de l'écran Kit & capteurs (`72×72 px`) | **Schéma du mât solaire et de ses 6 capteurs** : Situe visuellement le panneau solaire + batterie 12 V, l'abri météo BME280, la pompe/électrovanne, le débitmètre, la sonde d'humidité du sol (-20 cm) et la sonde NPK. Aide l'exploitant à localiser physiquement l'organe signalé en alerte. |

---

## 4. Groupe C — Enrichissement du catalogue `CropArt` (4 espèces maraîchères supplémentaires)

Dans [components/Illustrations.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Illustrations.tsx), le composant `CropArt` et son résolveur `resolveCropKind()` ont été enrichis de **4 nouvelles espèces** fréquentes dans les Niayes et la Vallée du Fleuve Sénégal, évitant la retombée sur la pousse générique (`seedling`) :

1. **`cabbage` (`chou`, `salade`, `laitue`)** : pomme de chou feuillue nervurée (`#2e6f40` / `#52b788`).
2. **`carrot` (`carotte`, `navet`)** : racine conique orangée striée et fanes vertes (`#e76f51` / `#2d6a4f`).
3. **`potato` (`pomme de terre`, `patate`)** : tubercules ocrés avec yeux caractéristiques (`#c99b52` / `#8a5a24`).
4. **`cassava` (`manioc`, `igname`)** : racines tubéreuses brunes et feuille palmée à 5 lobes (`#7f4f24` / `#2d6a4f`).

Ces icônes s'affichent automatiquement sur `/fr/parcelles`, `/fr/parcelles/[id]`, `/fr/cultures`, `/fr/campagnes`, `/fr/marches` et `/fr/rendement`.

---

## 5. Impact UX global par domaine métier

| Domaine métier | Avant | Après | Gain UX mesurable |
|---|---|---|---|
| **Foncier & Cultures** (`/fr/parcelles`, `/fr/exploitations`, `/fr/cultures`, `/fr/fertilisation`) | Même photo générique que la page de connexion ; icône `seedling` générique pour le chou, la carotte et la pomme de terre | Photo réelle de maraîchage au Lac Mbawane (Niayes) + illustrations dédiées `cabbage`, `carrot`, `potato`, `cassava` | Ancrage territorial sénégalais immédiat et reconnaissance visuelle instantanée des planches de culture |
| **Eau, Météo & Irrigation** (`/fr/irrigation`, `/fr/meteo`, `/fr/previsions`, `/fr/planning`) | Photo de champ généraliste sans rapport direct avec le réseau hydraulique | Photo plein cadre de ligne goutte-à-goutte au pied des cultures sur sol humide | Différenciation franche entre la gestion du foncier et le pilotage hydrique quotidien |
| **Santé des plantes & Ravageurs** (`/fr/maladies`, `/fr/risques`, `/fr/pieges`) | Bandeau générique + zone d'upload sans consigne visuelle de cadrage | Bandeau macro de feuillage de tomate + guide 3 vignettes `PhotoFramingGuide` + illustration `StickyTrapArt` sur les relevés de pièges | Meilleure qualité des clichés soumis au diagnostic foliaire et lecture intuitive des pièges jaunes englués |
| **IoT, Équipements & Alertes** (`/fr/kit`, `/fr/equipements`, `/fr/alertes`) | Aucune représentation physique du boîtier ou du mât capteur | Photo de station de télémesure solaire en plein champ + schéma `KitMastDiagram` annoté (6 capteurs) | Compréhension immédiate de l'architecture matérielle en bord de parcelle |
| **Marchés, Rendement & Rapports** (`/fr/marches`, `/fr/rendement`, `/fr/rapports`) | Photo de champ en culture sur les écrans économiques post-récolte | Photo de récolte d'oignons rouges et pommes de terre en caisses/sacs prête pour la commercialisation | Transition visuelle claire vers l'aval (récolte, cours ANSD/SIM/CSA en FCFA/kg et bilans de campagne) |

---

## 6. Captures Avant / Après

Toutes les captures ont été générées automatiquement par la suite Playwright (`e2e/visual-audit.spec.ts`) en résolutions Bureau (`1280×800`) et Mobile (`375×812`).

### 6.1 Domaine Foncier & Parcelles (`/fr/parcelles` — `parcelles-niayes.webp`)
- **Avant (Bureau)** : [before/bureau/parcelles.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/bureau/parcelles.png)
- **Après (Bureau)** : [bureau/parcelles.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/bureau/parcelles.png)
- **Avant (Mobile)** : [before/mobile/parcelles.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/mobile/parcelles.png)
- **Après (Mobile)** : [mobile/parcelles.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/mobile/parcelles.png)

### 6.2 Domaine Eau & Irrigation (`/fr/irrigation` — `irrigation-goutte.webp`)
- **Avant (Bureau)** : [before/bureau/irrigation.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/bureau/irrigation.png)
- **Après (Bureau)** : [bureau/irrigation.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/bureau/irrigation.png)
- **Avant (Mobile)** : [before/mobile/irrigation.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/mobile/irrigation.png)
- **Après (Mobile)** : [mobile/irrigation.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/mobile/irrigation.png)

### 6.3 Domaine Santé Végétale (`/fr/maladies` & `/fr/pieges` — `phyto-feuille.webp` + `PhotoFramingGuide` + `StickyTrapArt`)
- **Avant `/fr/maladies` (Bureau)** : [before/bureau/maladies.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/bureau/maladies.png)
- **Après `/fr/maladies` (Bureau)** : [bureau/maladies.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/bureau/maladies.png)
- **Avant `/fr/maladies` (Mobile)** : [before/mobile/maladies.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/mobile/maladies.png)
- **Après `/fr/maladies` (Mobile)** : [mobile/maladies.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/mobile/maladies.png)
- **Avant `/fr/pieges` (Bureau)** : [before/bureau/pieges.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/bureau/pieges.png)
- **Après `/fr/pieges` (Bureau)** : [bureau/pieges.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/bureau/pieges.png)

### 6.4 Domaine Matériel IoT & Alertes (`/fr/kit` — `kit-terrain.webp` + `KitMastDiagram`)
- **Avant (Bureau)** : [before/bureau/kit.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/bureau/kit.png)
- **Après (Bureau)** : [bureau/kit.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/bureau/kit.png)
- **Avant (Mobile)** : [before/mobile/kit.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/mobile/kit.png)
- **Après (Mobile)** : [mobile/kit.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/mobile/kit.png)

### 6.5 Domaine Récolte, Marchés & Rapports (`/fr/marches` — `recolte-marche.webp`)
- **Avant (Bureau)** : [before/bureau/marches.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/bureau/marches.png)
- **Après (Bureau)** : [bureau/marches.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/bureau/marches.png)
- **Avant (Mobile)** : [before/mobile/marches.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/before/mobile/marches.png)
- **Après (Mobile)** : [mobile/marches.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/mobile/marches.png)

---

## 7. Résultats des vérifications post-intégration

| Vérification | Commande exécutée | Résultat |
|---|---|---|
| **ESLint** | `npm run lint` | ✅ `0` erreur, `0` warning |
| **TypeScript** | `npm run typecheck` | ✅ `0` erreur |
| **Contrastes WCAG AA** | `npm run contrast` | ✅ `14/14` paires conformes en thèmes clair et sombre |
| **Tests unitaires & composants** | `npm test` (`vitest run`) | ✅ `31` fichiers de test / `630` tests passés |
| **Build de production Next.js** | `npm run build` | ✅ Succès (`103 kB` First Load JS partagé, toutes les routes générées sans erreur) |
| **Tests E2E Playwright & Audit Responsive** | `E2E_PROD=1 npx playwright test` | ✅ **`20/20` tests passés** (`visual-audit.spec.ts` : `23` routes × `4` viewports `375px`, `768px`, `1280px`, `1920px` = `0` débordement horizontal, `0` erreur console/CSP) |
