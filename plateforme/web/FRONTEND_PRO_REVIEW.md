# FRONTEND_PRO_REVIEW — Revue UX/UI produit (RBAC)

> Confidentiel — document réservé aux partenaires du projet SmartAgri92. Ne pas publier.
> Date : 2026-11-22. Revue, pas d'implémentation : aucun code modifié.

## 0. Méthode et limites (à lire d'abord)

- **Le parcours en direct dans Chrome n'a pas été fait** (outils navigateur déconnectés). Il est remplacé par l'examen des captures Playwright déjà produites (`audit-shots/rbac/` : 4 rôles × bureau, plus mobile agriculteur et menu mobile admin), en mode simulé, comptes `agriculteur@`, `cooperative@`, `agronome@`, `admin@demo.sn`.
- Conséquence : je juge le rendu, la hiérarchie et le contenu. Je ne juge ni la fluidité des interactions, ni les temps de chargement, ni les états de survol ou de focus.
- Les captures sont en pleine page : la barre latérale (bureau) apparaît coupée à la hauteur de l'écran et la barre basse mobile flotte au milieu de la page. Ce sont des artefacts de capture (éléments fixes), **pas des défauts retenus**. À confirmer en vrai.
- Les comparaisons avec John Deere Operations Center, Climate FieldView, EOSDA, OneSoil et Cropwise reposent sur ma connaissance générale de ces produits, pas sur un test côté à côté.
- Le code des quatre dashboards (`features/dashboard/Dashboard.tsx`, 931 lignes) n'a pas été relu ligne à ligne ; les constats viennent du rendu.

## 1. Audit UX des 4 dashboards

### Constat transversal

Les quatre rôles partagent le **même squelette** : bandeau héros (synthèse IA, météo, 4 compteurs), alerte critique, rangée de KPI, bloc Communauté, **grille de cartes parcelles**, « Sources des données ». La différenciation par rôle est réelle mais **mince** : elle tient à une ligne de sous-titre et à 1–3 blocs intercalés. Le sous-titre du héros est identique pour tous (« Le verdict de chaque parcelle d'abord… »), ce qui trahit le gabarit.

| Rôle | Pertinence métier | Charge cognitive | Clarté des KPI | Verdict |
|---|---|---|---|---|
| Agriculteur | Bonne : plan d'action du jour, besoin d'eau, prix oignon, parcelles | Moyenne à haute pour son public | Moyenne | Le plus abouti sur le fond |
| Coopérative | Bonne : périmètres, eau économisée, parc matériel, campagne | **Haute** | Moyenne | Riche mais dense |
| Agronome | Correcte : matrice de diagnostic par parcelle est le bon outil | Haute | Bonne dans la matrice | Matrice noyée sous les doublons |
| Admin | Correcte : supervision multi-organisations, répartition des alertes | Haute | Moyenne | Ressemble à un dashboard « tout-en-un » |

### Problèmes UX principaux

1. **Doublons de KPI dans la même page.** « Parcelles suivies » et « Parcelles sèches » figurent dans le héros **et** dans la rangée de KPI juste dessous (agriculteur, agronome ; coopérative et admin pour « parcelles sèches »). Impression de remplissage, perte de crédibilité.
2. **Le verdict IA contredit la page.** Agriculteur : « Tout est sous contrôle : aucune parcelle ne demande d'eau » alors qu'une **alerte critique** rouge est affichée juste dessous et une parcelle porte « 1 alerte ouverte ». Le message de réassurance et l'alerte se télescopent.
3. **« Confiance : Non communiquée » et « field_boundary v1 »** sont visibles dans la synthèse IA. Pour un agriculteur, c'est du jargon technique et un aveu d'information manquante. Place : rôle admin/agronome, pas le héros de l'agriculteur.
4. **La grille de parcelles est le plus gros défaut de hiérarchie.** Chaque carte empile 8 à 10 pastilles (kit, alertes, pH, besoin 24 h, température/humidité/pression, pompe, N-P-K, sondes, seuils) puis **3 boutons** (Voir la parcelle, Irrigation, Conseil IA). À 7 parcelles (admin) la page dépasse 4 900 px. C'est exactement le « rapport à rallonge » que les produits de référence évitent.
5. **Le verdict d'une parcelle n'est pas lisible d'un coup d'œil.** « Inconnu » (3 cartes sur 5–7) est l'état le plus fréquent en démo ; il ne dit pas quoi faire. Un état « Inconnu » sans action associée est un trou de confiance.
6. **Données incohérentes visibles en démo.** « 0 mm net (0 m³) / À irriguer dans les 24 h » : le badge dit d'irriguer, le chiffre dit 0. Coopérative : « 0 à arroser » partout mais « Besoin 24 h : 6,6 mm » sur les cartes. À corriger dans le jeu simulé ou le libellé.
7. **Blocs vides.** Agriculteur : le panneau « Conseils & alertes · Ndiol 2 » annonce « 1 alerte active » mais n'affiche aucun contenu, seulement deux boutons. Coopérative : « Parc matériel » a un grand vide au-dessus de la liste.
8. **Communauté sur le tableau de bord de chaque rôle**, y compris admin et agronome. Pertinent pour l'agriculteur, bruit pour l'admin. Le titre est une phrase de 10 mots.
9. **Aucune hiérarchie d'urgence.** Alerte critique, kits dégradés, kit silencieux, équipement en maintenance sont à des niveaux visuels voisins ; il manque un « à traiter maintenant » unique et ordonné.
10. **Rôle agronome : la matrice de diagnostic (le vrai outil métier) est en 3ᵉ rangée** après les doublons ; elle devrait ouvrir la page. Les boutons « NPK / Phyto » sont de bons raccourcis.

## 2. Audit UI

### Ce qui est professionnel

- **Système visuel cohérent** : verts agricoles, cartes arrondies, icônes de ligne homogènes, typographie sobre et lisible, mode sombre et sélecteur de langue (fr/wo/ff : rare et différenciant pour le Sénégal).
- **Honnêteté des données** : bandeau « Mode simulé : toutes les données sont fictives », fraîcheur (« il y a 4 min »), provenance. Excellent pour un jury et pour la confiance.
- **Menu par rôle** et pages bloquées gérées (RBAC visible : l'agriculteur n'a ni Exploitations ni Rapports ; l'agronome n'a pas Équipements).
- **Photographies de parcelles** et héros immersif : chaleur et ancrage terrain que n'ont pas les outils très « ingénieur ».
- **Mobile** : barre basse à 5 entrées (Accueil, Carte, Alertes, Assistant, Menu), menu coulissant avec groupes. Choix adapté à un usage terrain.

### Ce qui fait amateur

- **Même photo** (visage de la même personne) répétée sur **toutes** les cartes parcelles : tape-à-l'œil et répétitif dès 3 cartes. Sur 7 cartes (admin) l'effet est franchement artificiel.
- **Texte flou sur image** : le héros superpose texte, carte de synthèse translucide et photo ; le contraste du sous-titre et de « Synthèse automatique calculée… » (petit, gris sur flou) est limité.
- **Micro-typographie** : libellés de 10–11 px dans les cartes parcelles, « Parc matériel » et listes de kits ; illisibles en plein soleil sur téléphone, ce qui est le contexte réel.
- **Hiérarchie des boutons** : « Conseil IA » (vert plein) apparaît 4 à 8 fois par page ; il perd son statut d'action principale. Trois boutons empilés par carte et non alignés en bas de carte (hauteurs de cartes inégales, grands vides).
- **Grilles déséquilibrées** : 3 colonnes avec dernière rangée à 1–2 cartes laisse des trous ; plusieurs panneaux aux hauteurs étirées avec contenu au centre ou en bas.
- **Tableaux** : un seul vrai tableau (matrice agronome), correct. Ailleurs, listes de pastilles à la place de tableaux : on perd tri et comparaison à l'échelle de 20+ parcelles.
- **Mobile** : le héros prend l'écran entier avant le premier chiffre utile ; page de plus de 4 500 px en une colonne sans repli/accordéon.

### Comparaison avec les références

| Référence | Ce qu'elles font mieux | Où SmartAgri92 est meilleur |
|---|---|---|
| John Deere Operations Center | Carte au centre, liste filtrable, priorités de travail | Simplicité, langues locales, sans matériel Deere |
| Climate FieldView | Carte de parcelles + une métrique par parcelle, comparaison par saison | Conseils actionnables, alertes communautaires |
| EOSDA Crop Monitoring | Indices NDVI visuels sur carte, chronologie | Intégration capteurs au sol + irrigation |
| OneSoil | Parcours ultra-court, carte colorée, très peu de texte | Contexte sénégalais, IA conversationnelle |
| Cropwise | Registres/rapports propres, rôles et permissions | Prix du marché, communauté |

**Écart central :** les produits de référence sont **centrés sur la carte** et **une métrique par parcelle** ; SmartAgri92 est centré sur une **pile de cartes denses** et relègue la carte (`/carte`) au menu. Pour un agriculteur peu outillé, c'est la différence entre « je comprends en 5 secondes » et « je lis une fiche ».

## 3. Ressenti par rôle (parcours déduit des captures)

### Agriculteur (agriculteur@demo.sn)
- **Fonctionne :** la météo locale en grand, le plan d'action du jour, le prix de l'oignon, menu réduit à l'essentiel, boutons d'action sur chaque parcelle.
- **Déroute :** verdict rassurant + alerte critique contradictoires ; « Inconnu » ; « Confiance non communiquée » ; 10 pastilles par parcelle dont N-P-K et pression atmosphérique.
- **Amateur :** photo identique répétée, panneau « Conseils & alertes » vide, 0 mm avec « à irriguer ».
- **Professionnel :** héros immersif, météo 3 jours, mode simulé affiché, fr/wo/ff.

### Gestionnaire de coopérative (cooperative@demo.sn)
- **Fonctionne :** périmètres (Mboro, Potou), eau économisée, parc matériel 5/6, campagne.
- **Déroute :** 6 KPI + 4 panneaux + 5 cartes avant d'avoir une vue « quels agriculteurs ont un problème ». Il manque une vue **par membre/périmètre classée par urgence**.
- **Amateur :** « Campagne : Contre-saison froide (41 %) » comme valeur de KPI (texte long dans une carte chiffre) ; liste de matériel à puces minuscules ; vides dans les panneaux.
- **Professionnel :** notion de périmètres, matériel et eau économisée, très parlants pour une coopérative.

### Agronome (agronome@demo.sn)
- **Fonctionne :** matrice par parcelle avec raccourcis NPK/Phyto, diagnostics foliaires 30 j, Végétation (NDVI) dans le menu.
- **Déroute :** la matrice arrive après des doublons ; « Adoption des conseils IA : — » (tiret) est un KPI vide ; liste de kits non filtrable.
- **Amateur :** mêmes cartes parcelles à photo que l'agriculteur (outil de terrain, pas d'analyse).
- **Professionnel :** le tableau de diagnostic est le meilleur écran de la revue ; il mérite de devenir le cœur de la page.

### Admin (admin@demo.sn)
- **Fonctionne :** KPI de supervision (3 exploitations, 97 % kits, 33 408 mesures), répartition des alertes par règle, flotte de kits.
- **Déroute :** reste un dashboard « agriculteur en plus grand » (7 cartes parcelles) ; pas de vue santé plateforme (API, services IA, file d'alertes) en tête ; « répartition des alertes » en texte brut `soil_dry · 2`.
- **Amateur :** identifiants techniques (`soil_dry`, `device_offline`, `field_boundary v1`) affichés bruts.
- **Professionnel :** couverture multi-organisations et accès à tout le menu.

## 4. Recommandations (sans nouvelle fonctionnalité, ni service, ni route)

### P0 — à corriger avant toute démonstration

1. **Supprimer les doublons de KPI** (héros vs rangée) : garder un seul jeu de compteurs par page.
2. **Rendre le verdict IA cohérent avec l'alerte** : si une alerte critique est ouverte, le verdict ne dit pas « tout est sous contrôle » (règle de priorité dans le texte, pas dans les données).
3. **Corriger les incohérences visibles du jeu simulé** : « à irriguer » avec 0 mm ; « 0 à arroser » avec besoin 6 mm ; panneau « 1 alerte active » sans contenu ; KPI « — ».
4. **Alléger la carte parcelle** : verdict + une phrase d'action + 3 mesures clés ; le reste derrière « Voir la parcelle ». Un seul bouton principal par carte.
5. **Déjargonner** : « field_boundary v1 », « Confiance : Non communiquée », `soil_dry` → libellés métier ; détails techniques réservés à admin/agronome.
6. **Taille minimale de texte 12–13 px** sur mobile et dans les listes de kits/matériel.

### P1 — recommandé

7. **Différencier réellement les rôles** : sous-titre et ordre des blocs par rôle ; agronome = matrice en tête ; coopérative = périmètres classés par urgence ; admin = supervision d'abord, parcelles en lien « voir toutes ».
8. **Limiter les parcelles du tableau de bord** à 3 à 4 (les plus urgentes) + lien « Toutes les parcelles » ; sur mobile, accordéons pour Communauté et Sources.
9. **Placer la carte plus haut** pour l'agriculteur (miniature colorée par verdict) : alignement sur OneSoil/FieldView.
10. **Retirer Communauté** du tableau de bord admin et agronome (garder dans le menu).
11. **Photos** : varier ou remplacer par une icône de culture sur fond uni pour les cartes ; réserver la photo au héros.
12. **Hauteur égale des cartes** et boutons alignés en bas ; éviter la dernière rangée orpheline.
13. **« Conseil IA » : un seul bouton primaire** par zone, les autres en secondaire.
14. **État « Inconnu »** : ajouter la raison (« pas de kit », « capteur silencieux ») et l'action.

### P2 — cosmétique

15. Contraste et flou du texte sur le héros ; ombre de texte ou voile plus sombre.
16. Valeur longue en KPI (« Contre-saison froide ») : titre court + sous-ligne.
17. Liste de matériel en tableau compact (tri par statut).
18. Titre « Communauté & alertes entre agriculteurs (maladies, insectes, oiseaux) » raccourci.
19. Uniformiser les tailles d'icônes et l'espacement des listes de kits.

## 5. Conclusion obligatoire

### 1) Niveau actuel du produit : **Correct (haut de fourchette)**

- Au-dessus d'« Amateur » : système visuel cohérent, RBAC visible, honnêteté sur les données, langues locales, bon mobile de base.
- En dessous de « Professionnel » : surcharge d'information, doublons, incohérences de contenu, rôles trop semblables, photos répétées. Ces défauts sont **de hiérarchie et d'édition**, pas d'architecture : ils se corrigent sans nouvelle fonctionnalité.
- « Premium » : non, tant que la carte reste secondaire et que la densité n'est pas maîtrisée.

### 2) Préparation par usage

| Usage | Prêt ? | Condition |
|---|---|---|
| **Démo Jury** | **Oui, sous réserve** | Corriger P0 1–3 (doublons, verdict contradictoire, incohérences) ; le reste passe, le jury appréciera l'honnêteté « mode simulé » et les langues locales |
| **Investisseur** | **Pas encore** | P0 complet + P1 7–9 : l'investisseur compare à FieldView/OneSoil et jugera la densité et l'absence de carte |
| **Client pilote** | **Non, pas en l'état** | Nécessite P0 + P1, surtout cartes allégées et lisibilité mobile en plein soleil ; avec données réelles, les états « Inconnu » deviendront un problème de confiance |
| **Commercialisation MVP** | **Non** | P0 + P1 + test utilisateur terrain avec de vrais agriculteurs ; cette revue ne remplace pas un test d'usage |

### Réserve finale
Ces avis sont **sans test utilisateur réel et sans parcours Chrome en direct**. Je recommande de les confirmer en faisant utiliser l'écran agriculteur par 3 à 5 vrais agriculteurs avant tout engagement « client pilote ».
