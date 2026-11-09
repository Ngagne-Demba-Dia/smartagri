# 19. Audit du Frontend et plan de refonte vers la version candidate

> **Confidentiel — réservé aux partenaires de travail.** Document local, à ne publier nulle part.
>
> Version 1, 09/11/2026. Périmètre : `plateforme/web/` uniquement. Rien n'est touché dans le backend, les contrats (18 services), le doc 16 (baseline IA v1 gelée), les hooks, les routes ni les tests existants.
> Ce document couvre l'étape 1 de la mission (audit) et prépare les étapes 2 à 12. Aucun code n'a été modifié pour l'écrire.

## 1. Résumé

Le Frontend est solide sur le fond et mince sur la forme.

- **Fond.** 13 services sur 18 ont un écran. Les règles d'honnêteté (confiance non calibrée jamais en pourcentage, périmé jamais présenté comme frais, valeur de secours signalée, abstention sous 0,7) sont codées et testées. 521 tests, build vert, typecheck et lint à zéro avertissement.
- **Forme.** Le dépôt reprend déjà la palette du prototype, mais pas son pouvoir de séduction : aucune photo, aucun relief, des indicateurs réduits à un libellé et un nombre, pas de squelette de chargement, pas d'illustration, police système.
- **Trous mesurés.** Cinq services sans écran (2, 4, 10, 11, 15). Quatre modules à moitié finis (Cultures, Campagnes, Rendement, Équipements). Wolof et pulaar : fichiers de messages vides (0 clé sur 652). Aucun test navigateur ni test de composant. Les écrans n'ont jamais été validés dans un navigateur à plusieurs tailles.

Le chemin vers « 99 % » passe par six vagues (§ 10). Trois décisions du propriétaire du projet sont nécessaires avant la vague 1 (§ 11).

## 2. État mesuré

| Mesure | Valeur | Source |
|---|---|---|
| Routes applicatives | 18 dossiers + `error.tsx` + `layout.tsx` (connexion à part) | `app/[locale]/(app)/` |
| Services avec écran | 13 sur 18 | docs 17 et 18 |
| Services sans écran | 2 `soil_forecast`, 4 `irrigation_plan`, 10 `trap_counts`, 11 `vegetation`, 15 `price_forecast` | registre des contrats |
| Hooks et mocks des 5 services manquants | **Déjà présents** (`services/ai/*`, `mocks/handlers/ai.ts`, schémas zod) | lecture du code |
| Coquilles | `CropsShell` 53 l., `CampaignsShell` 39 l., `YieldShell` 66 l., `EquipmentShell` 59 l. | `features/shells/` |
| Tests | 521 réussis, 21 fichiers, environnement Node sans DOM | vitest |
| Couverture | 97,69 % lignes… mais limitée à `lib/`, `services/`, `mocks/` : **les composants React ne sont pas mesurés** | `vitest.config` |
| Messages | `fr.json` 652 clés ; `wo.json` et `ff.json` : 0 clé | `messages/` |
| Tests navigateur / composants | Aucun (ni Playwright, ni Testing Library, ni jsdom) | `package.json` |
| Points d'arrêt responsive utilisés | `md:` 21, `sm:` 5, `lg:` 1, `xl:` 1 | grep |
| Attributs d'accessibilité | `aria-label` 16, `aria-labelledby` 14, `aria-live` 5, `aria-invalid` 5, `aria-current` 2 | grep |
| Dépendances installées mais non utilisées | `lucide-react`, `motion`, `@radix-ui/react-slot`, `@radix-ui/react-tabs`, `class-variance-authority` | grep des imports |
| Dossier `public/` | Absent (ni photo, ni police, ni illustration) | arborescence |

## 3. Écrans : terminés, partiels, manquants

| Écran | Route | Statut | Remarque |
|---|---|---|---|
| Connexion | `/login` | Terminé (fond) | Visuel nu, comptes de démonstration en liste |
| Tableau de bord | `/tableau` | Terminé (fond), pauvre en forme | KPI = libellé + nombre, aucun repère de tendance |
| Exploitations, Parcelles (+ fiche) | `/exploitations`, `/parcelles` | Terminé | Liste sans vignette ni jauge |
| Carte | `/carte` | Terminé | Leaflet, 3 couches, table équivalente ; style par défaut |
| Météo | `/meteo` | Terminé | Cartes sans icône de condition |
| Irrigation | `/irrigation` | Terminé (service 3) | Pas encore de planning (service 4) |
| Fertilisation | `/fertilisation` | Terminé (service 5) | |
| Risques | `/risques` | Terminé (service 9) | |
| Recommandations | `/recommandations` | Terminé (service 5) | |
| Assistant | `/assistant` | Terminé (16 et 17) | Saisie vocale livrée au sprint B |
| Maladies | `/maladies` | Terminé (service 8) | Abstention sous 0,7 |
| Kit | `/kit` | Terminé (7 et 13) | |
| Alertes | `/alertes` | Terminé | |
| Rapports | `/rapports` | Terminé | KPI + économie d'eau (service 14) |
| Équipements | `/equipements` | **Partiel** | Inventaire + santé ; pas d'historique, pas de parc par état |
| Cultures | `/cultures` | **Partiel** | Table des cycles, branchée sur `GET /v1/fields/{id}/crop-cycles`, mais habillée en « module prévu » |
| Campagnes | `/campagnes` | **Partiel** | Même cas, `GET /v1/campaigns` |
| Rendement | `/rendement` | **Partiel** | Lit le service 12 ; reste dans la coquille « prévu » |
| Prévision d'humidité (service 2) | — | **Manquant** | |
| Plan d'irrigation de l'exploitation (service 4) | — | **Manquant** | |
| Comptage de pièges (service 10) | — | **Manquant** | |
| Végétation NDVI (service 11) | — | **Manquant** | |
| Prix de marché (service 15) | — | **Manquant** | |

## 4. Audit UX/UI

### 4.1 Incohérences visuelles

1. **Cartes toutes identiques.** `.card` unique (fond blanc, bordure fine, rayon 14). Une alerte critique, un KPI et une note ont le même poids visuel.
2. **Aucune élévation.** Pas d'ombre, pas de couche : l'écran est plat, sans hiérarchie de profondeur.
3. **Typographie système.** Aucune échelle (titres, chiffres, légendes), aucun chiffre tabulaire pour les valeurs alignées.
4. **En-tête.** Le nom en texte brut, pas de logo, pas de bascule de thème, pas de largeur maximale sur grand écran.
5. **Icônes.** `Icon.tsx` maison, alors que `lucide-react` est installé sans être utilisé.
6. **Graphiques.** Un seul composant (`Chart.tsx`, recharts) ; thème correct, mais pas de dégradé sous la courbe, pas d'info-bulle soignée.
7. **Jetons dupliqués.** Le bloc sombre est écrit deux fois dans `globals.css` (`prefers-color-scheme` et `data-theme="dark"`).
8. **Tailwind ne scanne pas `lib/`.** Une classe écrite dans un fichier de `lib/` serait purgée (piège pour la refonte).

### 4.2 Incohérences UX

1. **Chargement.** `QueryState` affiche un texte « chargement », sans squelette : l'écran saute à l'arrivée des données.
2. **États vides.** Une phrase seule, sans illustration ni action proposée.
3. **Erreurs.** Message correct, mais bouton « Réessayer » seul ; pas de distinction visuelle entre « hors ligne », « non publié » et « erreur serveur ».
4. **Modules « prévus ».** Quatre écrans fonctionnels portent la mention « prévu en V1.1 », ce qui les fait passer pour des maquettes.
5. **Mobile.** `BottomBar` présente, mais jamais vérifiée en navigateur : débordements de tables et de graphiques possibles.
6. **Pas de retour d'action.** Pas de notification discrète après une écriture (seuils, accusé d'alerte).

### 4.3 Accessibilité

À conserver (acquis) : lien d'évitement, `:focus-visible` à 3 px, `prefers-reduced-motion`, cibles tactiles de 44 px, tiroir en `<dialog>` natif, vue tableau de chaque graphique, `aria-current`, état toujours dit en couleur + icône + mot.

À vérifier ou corriger : contrastes AA des jetons (jamais mesurés), ordre de tabulation des écrans composés, annonces `aria-live` lors des changements de résultat, texte alternatif des futures illustrations, zoom 200 %, lecture au lecteur d'écran, taille minimale du texte secondaire (`text-xs`).

### 4.4 Dette technique Frontend

- Composants React non mesurés par la couverture ; aucun test de rendu.
- Aucun test de bout en bout (authentification, parcours, assistant, irrigation, maladies, recommandations, rapports).
- Wolof et pulaar : mécanisme de repli présent (bannière), contenu absent.
- Dépendances inutilisées (cinq) qui gonflent l'installation sans servir.
- `MockBanner` de 222 lignes dans `features/dev/` : outil de développement, à garder hors de la charge visuelle.
- Les quatre coquilles à fusionner dans de vrais modules.

## 5. Comparaison avec le prototype « Tableau de bord du champ »

Le prototype (page unique, 139 Ko dont l'essentiel en image encodée) est la référence graphique. Il n'est jamais modifié.

### 5.1 Ce que le dépôt a déjà

La palette en variables (`--bg`, `--card`, `--ink`, `--mute`, `--line`, `--g`, `--soft`, `--amber`, `--red`), les trois thèmes (clair, sombre automatique, sombre manuel), les teintes de statut, les rayons 14 px / 10 px et le principe « couleur + icône + mot ». **La refonte n'est donc pas un recolorage.**

### 5.2 Ce que le prototype a de plus

| Élément | Prototype | Dépôt | Effet |
|---|---|---|---|
| Héros | Photo de parcelle sous dégradé vert (90°, 180° sur mobile), 320 à 360 px de haut, texte blanc, pastilles | Aucun | Immersion, identité agricole immédiate |
| Indicateur « en direct » | Point animé (`pulse` 1,6 s) | Aucun | Sensation de donnée vivante |
| Valeur | 2 rem, 800, unité en `small` atténuée | Libellé + nombre | Lecture en un coup d'œil |
| Jauge | `.meter` 10 px, pilule | Aucune | Niveau perceptible sans lire le nombre |
| Interrupteur | `.sw` 52 × 28, transition 0,2 s | Cases standard | Contrôle tactile clair |
| Alerte | Fond carte, **liseré gauche de 4 px** coloré | Bandeau plein | Hiérarchie des sévérités |
| Étiquettes | Pilules `ok / warn / bad` à teinte douce | `StatusTag` (équivalent) | Déjà proche |
| Onglets | Boutons segmentés `.tabs` | Aucun | Période Jour / Semaine / Mois / Année |
| Bandeau critique | Bordure 2 px rouge, clignotement | `SyncBanner` | Urgence perceptible |
| En-tête | Logo, bascule de thème, largeur 1100 px | Texte, pas de bascule, pleine largeur | Cohérence de marque |
| Grille | `auto-fit, minmax(230px,1fr)` | Grilles fixes par écran | Adaptation naturelle |

### 5.3 À ne pas reproduire

- Le prototype est un écran **de kit**, hors ligne, sans route ni provenance : pas de bloc d'honnêteté IA, pas de langues.
- Les zones « OLED » simulées et le clignotement continu (gênant en accessibilité : à borner par `prefers-reduced-motion`).
- Une confiance inventée (« 94 % ») : déjà proscrite par le doc 10.
- Les textes de la section de présentation de la page : jamais repris.

### 5.4 Ce qui rend le prototype moderne

Un héros photographique, des chiffres grands avec leur unité, des jauges, des pastilles douces, un seul accent vert, beaucoup d'air, une animation unique et lente. **Le dépôt doit emprunter ces cinq procédés et les relier à ses propres règles de provenance.**

## 6. Système de design cible

### 6.1 Contraintes techniques de la politique de sécurité (CSP)

- Pas d'attribut `style=` dans le HTML serveur : largeurs dynamiques par attribut SVG (`width`, `stroke-dasharray`) ou par classes quantifiées (`w-[10%]`… générées par pas de 5 %).
- Images : fichiers statiques de `public/` ou `data:` ; pas de service externe.
- Polices : **auto-hébergées** (`font-src 'self'`). Aucune feuille Google Fonts.
- Aucun script tiers.

### 6.2 Jetons (une seule source, sans doublon)

Les jetons existants sont conservés ; on les range en un bloc unique par thème et on ajoute :

| Famille | Jetons ajoutés |
|---|---|
| Surfaces | `--surface-1` (page), `--surface-2` (carte), `--surface-3` (carte en relief), `--overlay` |
| Accents | `--g-050…--g-900` (rampe verte), `--sky` (eau), `--earth` (terre), `--sun` (soleil) |
| Élévation | `--shadow-1` (repos), `--shadow-2` (survol), `--shadow-3` (tiroir, dialogue) ; en sombre : bordure plus claire plutôt qu'ombre |
| Dégradés | `--grad-hero`, `--grad-card-ok`, `--grad-card-warn`, `--grad-card-bad` (très discrets) |
| Rayons | `--r-sm` 8, `--r-md` 10, `--r-lg` 14, `--r-xl` 20, `--r-pill` 999 |
| Espacement | échelle 4 px : 4, 8, 12, 16, 24, 32, 48, 64 |
| Mouvement | `--dur-fast` 120 ms, `--dur` 200 ms, `--dur-slow` 400 ms ; `--ease` courbe douce ; tout ramené à 0 par `prefers-reduced-motion` |

**Contrastes.** Chaque paire texte/fond sera mesurée par un script (rapport de contraste ≥ 4,5 pour le texte, ≥ 3 pour les grands textes et les contours d'interface) avant d'être figée.

### 6.3 Typographie

Une famille de variable auto-hébergée (candidat : Inter, licence libre), chargée par `next/font/local` à partir d'un fichier de `public/fonts/`. Échelle : 12 / 14 / 16 / 18 / 24 / 32 / 44. Chiffres tabulaires (`tabular-nums`) pour tous les KPI et tables. Poids 400, 600, 800 seulement.

### 6.4 Visuels

- Photo de héros : image de parcelle verte du prototype, extraite en local, recompressée (≤ 150 Ko, WebP), placée dans `public/img/`. Aucun nom de personne dans le nom du fichier ni dans le texte alternatif (« Parcelle de légumes sous filet »).
- Illustrations d'états vides et d'erreur : SVG en ligne, trait vert, quatre motifs (parcelle vide, nuage, capteur déconnecté, feuille), écrits à la main, sans dépendance.
- Icônes : adoption de `lucide-react` (déjà installé), importées une par une pour l'élagage ; `Icon.tsx` devient une façade.

## 7. Bibliothèque de composants

Tous sont **visuels**. Ils s'insèrent dans l'existant sans changer les props métier.

| Composant | Rôle | Remplace / complète |
|---|---|---|
| `AppShell` v2 | Barre latérale repliable, en-tête avec logo, sélecteur de langue, **bascule de thème** (clair / auto / sombre mémorisé) | `AppShell`, `Sidebar`, `LocaleSwitcher` |
| `Hero` | Photo + dégradé + titre + pastilles + point « en direct » | nouveau (Tableau de bord, Connexion) |
| `KpiCard` | Libellé, valeur 32 px, unité atténuée, tendance (flèche + écart), mini-courbe SVG ou jauge | tuiles du tableau de bord et des rapports |
| `Meter` | Jauge pilule 10 px, seuils marqués | nouveau |
| `Sparkline` | Mini-courbe SVG sans axes, avec alternative textuelle | nouveau |
| `FieldCard` | Parcelle : culture, humidité (jauge), alertes, statut de la pompe | lignes de `FieldsList` |
| `WeatherCard` | Icône de condition, température, pluie, vent, fraîcheur | cartes de `WeatherView` |
| `AiCard` | Cadre commun des résultats d'IA : titre, **badge de confiance**, provenance repliable, âge | habille les résultats des services 2, 3, 4, 5, 8, 9, 10, 11, 12, 15 |
| `ConfidenceBadge` | Pourcentage **seulement** si calibrée ; sinon « non calibrée » ; sinon « incertain » | `confidenceView`, `probabilityView` (logique inchangée) |
| `ProvenanceNote` v2 | Modèle, version, date, repli ; pliable | `Provenance.tsx` (même données) |
| `StatusTag` v2 | Pilule + icône + mot, teintes douces | `StatusTag` |
| `AlertRow` | Liseré gauche de 4 px par sévérité | liste des alertes |
| `Skeleton`, `SkeletonCard`, `SkeletonChart` | Chargement avec forme finale | `QueryState` (état « en cours ») |
| `EmptyState` | Illustration + phrase + action | `QueryState` (état « vide ») |
| `ErrorState` | Illustration + cause (hors ligne, non publié, serveur) + réessayer | `QueryState` (état « erreur ») |
| `Segmented` | Onglets segmentés (période, couche, horizon) | nouveau (pas de nouvelle dépendance : base `@radix-ui/react-tabs` déjà installée) |
| `Toggle` | Interrupteur 52 × 28 accessible (`role="switch"`) | cases à cocher d'options |
| `Toast` | Retour d'action discret, `aria-live="polite"` | nouveau |
| `DataTable` v2 | En-tête collant, lignes denses/aérées, défilement latéral sur mobile avec ombre de bord | `DataTable` |
| `Chart` v2 | Dégradé sous la courbe, info-bulle soignée, bande p10–p90 | `Chart.tsx` |
| `Steps` | Étapes d'un cycle (semis, croissance, récolte) | Cultures, Campagnes |

**Décision sur les dépendances.** Adopter `lucide-react` et `@radix-ui/react-tabs`. Utiliser `class-variance-authority` pour les variantes de cartes et de pilules. Utiliser `motion` seulement pour l'entrée des listes et du tiroir, avec repli sans animation. Retirer `@radix-ui/react-slot` s'il reste inutilisé à la fin.

## 8. Plan écran par écran

Légende : **C** conserver, **A** améliorer, **R** remplacer.

| Écran | Conserver | Améliorer | Remplacer |
|---|---|---|---|
| **Tableau de bord** | Données, hooks, liens | KPI en `KpiCard` avec unité, tendance, mini-courbe ; cartes d'alertes | **Remplacer** l'ouverture par un `Hero` (nom de l'exploitation, météo du jour, point « en direct », pastilles d'état) |
| **Parcelles** (liste, fiche) | Filtres, tri, fiche, formulaire de seuils | Liste en `FieldCard` ; fiche avec courbe d'humidité à dégradé et seuils tracés ; `Toggle` pour la pompe | Rien |
| **Carte** | Leaflet, couches, table équivalente, tiroir | Tuiles et teintes de la rampe verte, légende compacte, `Segmented` pour les couches | Contrôles Leaflet par défaut |
| **Météo** | Données, fraîcheur | `WeatherCard` à icônes, prévision sur 5 jours en bande, bascule heure/jour | Cartes sans icône |
| **Irrigation** | Calcul, diviseur, report de pluie | `AiCard` avec `ConfidenceBadge`, volume en grand, jauge de besoin, bande p10–p90 | Résultat en texte |
| **Fertilisation** | Doses, justification | `AiCard`, barres N/P/K avec `Meter` | Liste de doses sèche |
| **Risques** | Niveaux dérivés des lignes | Carte de chaleur parcelle × ravageur avec libellés ; `AlertRow` | Tableau seul |
| **Assistant** | Chat, micro, brouillon relu | Bulles avec avatar, citations repliables, état « l'assistant écrit », entrée collée en bas sur mobile | Zone de saisie nue |
| **Rapports** | KPI, export, économie d'eau | `KpiCard`, `Chart` v2, `Segmented` de période | Tuiles sèches |
| **Alertes** | Accusé de réception, filtres | `AlertRow` à liseré, regroupement par sévérité, `Toast` à l'accusé | Bandeaux pleins |
| **Équipements** | Inventaire, santé du kit | **Compléter** : parc par état (vignettes), batterie, dernier contact, historique des pannes | Habillage « module prévu » |
| Kit, Maladies, Connexion | Logique complète | `AiCard`, `Hero` (connexion), aperçu de photo encadré | Rien |

## 9. Fermer les modules manquants et partiels

### 9.1 Cinq services sans écran (hooks et mocks prêts)

| Service | Écran proposé | Contenu | États exigés |
|---|---|---|---|
| **2** `soil_forecast` | Onglet « Prévision » de la fiche parcelle + route `/previsions` | Courbe d'humidité à 24/48/72 h, **bande p10–p90**, seuils de départ/arrêt tracés, « arrosage conseillé » dérivé | chargement, erreur, vide, périmé, repli, non calibré |
| **4** `irrigation_plan` | Route `/planning` | Frise horaire par pompe (créneaux), volume par créneau, total du jour, sélecteur de date | idem ; jour sans créneau = état vide explicite |
| **10** `trap_counts` | Route `/pieges` | Courbe de comptage par ravageur, seuil d'alerte, dernière photo si `image_id`, comparaison avec le risque (service 9) | idem |
| **11** `vegetation` | Onglet « Végétation » de la fiche parcelle | NDVI et EVI, points comblés distingués, stade BBCH, couverture, `Segmented` de période | idem |
| **15** `price_forecast` | Route `/marches` | Prix observé, prévision à 1 à 4 semaines avec bande p10–p90, choix de culture et de marché | idem ; culture inconnue = état vide avec liste proposée |

Chaque écran suit le motif existant (`page.tsx` → `XView.tsx` → `lib/x.ts` → `tests/x.test.ts` → clés `fr.json`) et réutilise `AiCard`, `ConfidenceBadge`, `ProvenanceNote`. La navigation reçoit ses entrées par `lib/modules.ts`, sans toucher aux routes existantes.

**Point à signaler.** Les routes de ces cinq services sont marquées « proposées » dans le registre : l'écran sera complet en mode simulé, mais l'appel réel dépendra du Backend (étape ultérieure).

### 9.2 Quatre modules partiels

| Module | Déjà là | À ajouter |
|---|---|---|
| **Cultures** | Table des cycles par parcelle | Sortie de la coquille ; vue `Steps` du cycle actif ; fiche culture (variété, dates, rendement) ; filtres par statut ; états complets |
| **Campagnes** | Table (`GET /v1/campaigns`) | Cartes par campagne (saison, statut, dates, parcelles liées), frise des saisons, filtres |
| **Rendement** | Lecture du service 12 | Courbe p10–p50–p90 à l'échelle de la parcelle, comparaison entre cycles, `AiCard` avec confiance |
| **Équipements** | Inventaire + santé | Parc par état, batterie, dernier contact, lien vers le Kit ; historique des pannes |

**Limite.** Aucune route d'écriture n'existe pour créer une culture ou une campagne : « complet » signifie ici **lecture complète, états complets, visuel complet**. La création sera une tâche de la phase Backend.

## 10. Priorisation en six vagues

| Vague | Contenu | Effort | Risque | Livrable vérifiable |
|---|---|---|---|---|
| **0. Outils** | Validation navigateur : Playwright (une dépendance de développement) ; Testing Library + jsdom ; script de contraste | ½ jour | Téléchargement des navigateurs | Une capture par écran et par taille |
| **1. Socle visuel** | Jetons uniques, police auto-hébergée, `lucide-react`, bascule de thème, `AppShell` v2, `Skeleton`, `EmptyState`, `ErrorState`, `Toast`, `QueryState` v2 | 2 jours | Moyen (touche tous les écrans) | Aucun test existant modifié ; 521 tests verts |
| **2. Composants de données** | `KpiCard`, `Meter`, `Sparkline`, `AiCard`, `ConfidenceBadge`, `ProvenanceNote` v2, `AlertRow`, `Segmented`, `Toggle`, `DataTable` v2, `Chart` v2 | 2 jours | Moyen | Tests de rendu de chaque composant |
| **3. Écrans existants** | Habillage des 14 écrans du § 8, `Hero`, photo | 2 jours | Faible | Captures avant/après |
| **4. Services et modules** | Écrans 2, 4, 10, 11, 15 ; Cultures, Campagnes, Rendement, Équipements complets ; retrait des coquilles | 3 jours | Moyen | Tests des calculs purs + rendu |
| **5. Langues, accessibilité, responsive** | Wolof et pulaar (§ 11) ; passes AA ; 4 tailles | 2 jours + traduction externe | Élevé pour les langues | Rapport de contraste, parcours clavier |
| **6. Tests et clôture** | Playwright (authentification, parcours, assistant, irrigation, maladies, recommandations, rapports), Testing Library, six commandes vertes, doc 20 | 2 jours | Faible | `20_frontend_release_candidate.md` |

Ordre imposé : 0 → 1 → 2 → 3 → 4 → 5 → 6. Les vagues 1 à 3 donnent seules l'essentiel de l'effet « produit premium ».

## 11. Décisions et réserves

1. **Wolof et pulaar.** Le doc 10 § 6 interdit les textes inventés. Je peux préparer l'extraction des 652 clés (fichier de travail clé / français / traduction / relecteur) et un repli clé par clé vers le français ; je ne remplirai pas ces deux langues moi-même sans relecture par des locuteurs : une traduction approximative de messages sur l'irrigation ou les maladies est un risque pour l'utilisateur. **Décision attendue :** qui traduit et relit, ou accepter le repli français comme état « langues disponibles ».
2. **Dépendances de test.** Playwright (et le téléchargement de ses navigateurs), Testing Library, jsdom. Versions épinglées, vieilles d'au moins deux semaines, vérifiées avant installation. **Accord attendu.**
3. **Police et photo.** Inter auto-hébergée (licence libre) et photo de parcelle extraite du prototype, locale seulement. **Accord attendu**, notamment sur l'usage de la photo hors du fichier d'origine.
4. **« 99 % ».** Défini ici comme : 18 services sur 18 avec écran, aucun module « prévu », six commandes vertes, parcours Playwright verts, contrastes AA mesurés, 4 tailles validées. Les langues wo/ff en dépendent de la décision 1.
5. **Hors périmètre, nommément :** FastAPI, Backend, OctOpus ML, firmware, infrastructure, Kubernetes, MQTT, déploiement, création de cultures ou de campagnes.

## 12. Règles tenues pendant la refonte

- Une seule vague à la fois, six commandes (prettier 110, typecheck, lint à zéro avertissement, i18n:check, vitest, build) avant de passer à la suivante.
- Les règles d'affichage de l'IA sont intouchables : pas de pourcentage sans calibration, jamais de périmé présenté comme frais, « valeur de secours » si `fallback_step > 0`, abstention sous 0,7.
- Fichiers sous 800 lignes. Aucune donnée du projet envoyée à un service externe.
