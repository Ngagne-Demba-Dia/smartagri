# 34 — Revue humaine complète du produit Web (Phase E1)

**Statut** : Exécuté et vérifié — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : inspection visuelle et fonctionnelle complète des 24 écrans de l'application Web SmartAgri92 (incluant les 19 écrans prioritaires exigés : Login, Dashboard, Exploitations, Parcelles, Détail Parcelle, Carte, Météo, Irrigation, Fertilisation, Risques, Assistant, Recommandations, Rapports, Équipements, Alertes, Maladies, Campagnes, Cultures, Rendement + Kit, Humidité prévue, Planning, Pièges, Végétation, Marchés) aux 4 résolutions cibles (`375×800` mobile, `768×1024` tablette, `1280×800` portable, `1920×1080` bureau).

---

## 1. Grille d'évaluation globale sur les 11 critères

| Critère | Constat initial (avant durcissement E4) | État après durcissement E4 |
|---|---|---|
| **1. Cohérence visuelle** | Charte « Premium AgriTech » homogène (verre dépoli, bannières photographiques à liseré d'état, typographie Inter, cartes `card` / `card-ai`). | **100 % conforme** |
| **2. Responsive** | 0 débordement horizontal (`scrollWidth <= innerWidth`) sur les 23 écrans connectés + Login de `375 px` à `1920 px`. Barre inférieure mobile (`BottomBar`) et tiroir `<dialog>` fonctionnels. | **100 % conforme** |
| **3. Lisibilité** | Hiérarchie `h1` → `h2` → `h3` claire, chiffres `tabular-nums`, contrastes WCAG AA vérifiés en thème clair et en thème sombre. | **100 % conforme** |
| **4. Orthographe & langue** | 5 irritants repérés : `Azote indicatif eleve.` (accent manquant), `Moteur vreco_engine@2` (préfixe `v` doublé), `Saison dry` (anglais), `Règle pump_fault` (identifiant technique brut), `leave-one-season-out` (jargon anglais) et `Lot OctOpus` (nom de code interne). | **Corrigés à 100 % en Phase E4** |
| **5. Unités** | Unités agronomiques normalisées (`mm`, `m³`, `kg/ha`, `mg/kg`, `%`, `°C`, `t/ha`, `m³/h`, `FCFA/kg`). Un cas de `-0 %` détecté sur *Prix du marché* et une équivalence terrain (`1 mm = 1 L/m²`) ajoutée sur *Irrigation*. | **Corrigés à 100 % en Phase E4** |
| **6. Alignements** | Sur *Recommandations*, l'icône de bulle de dialogue était empilée au-dessus du motif au lieu d'être alignée en ligne ; sur *Assistant*, le bouton de dictée et le compteur de caractères étaient empilés verticalement. | **Corrigés à 100 % en Phase E4** |
| **7. Boutons** | Hauteur tactile minimale `min-h-touch` (`44 px`), états `:disabled` explicites pendant les mutations (`Envoi…`, `Analyse en cours…`, `Acquittement…`, `Enregistrement…`). | **100 % conforme** |
| **8. Icônes** | Jeu d'icônes vectorielles cohérent (`Icon.tsx`) + illustrations SVG (`CropArt`, `SkyArt`, `AdvisorAvatar`, `Furrows`) toutes décoratives (`aria-hidden="true"`). | **100 % conforme** |
| **9. États vides** | Chaque liste, graphique ou sélecteur dispose d'un message d'état vide dédié (`EmptyState` / `QueryState` : *« Aucune alerte. »*, *« Aucun cycle dans cet état. »*, etc.). | **100 % conforme** |
| **10. Chargements** | Squelettes (`Skeleton`) et annonces `Chargement…` non bloquantes ; aucun écran figé. | **100 % conforme** |
| **11. Erreurs** | Messages d'erreur traduits par code d'enveloppe (`errors.*`), bouton `Réessayer` sur chaque `QueryState`, validation de plage de dates sur *Rapports* et validation de seuils sur *Détail Parcelle*. | **100 % conforme** |

---

## 2. Revue détaillée écran par écran

### 2.1 Connexion (`/fr/login`)
- **Visuel & Responsive** : mise en page en 2 colonnes sur bureau (accroche éditoriale + carte de connexion) et 1 colonne centrée sur mobile (`375 px`). Bascule de thème clair/sombre et sélecteur de langue accessibles en haut du formulaire.
- **Formulaire & Erreurs** : étiquettes explicites (`Identifiant`, `Mot de passe`), validation côté client (`Saisissez votre identifiant et votre mot de passe.`) et message d'alerte `role="alert"` en cas d'identifiants invalides.
- **Aide démo** : cartes des comptes de démonstration en un clic (Agriculteur, Gestionnaire de coopérative, Agronome, Administrateur) affichées uniquement en mode simulé.

### 2.2 Tableau de bord (`/fr/tableau`)
- **Visuel & Hiérarchie** : bannière héroïque regroupant la **Synthèse de l'IA** (`AiSummary`), la **Météo de la parcelle prioritaire** (`WeatherPanel` à 3 jours) et les **4 KPI** (`Parcelles suivies`, `Parcelles sèches`, `Kits silencieux`, `Alertes ouvertes`).
- **Cartes Parcelles (`FieldLiveCard`)** : anneau SVG d'humidité (`MoistureRing`), jauge `Meter` avec repères des seuils de démarrage et d'arrêt, capsules d'état du kit et boutons d'action (`Voir la parcelle`, `Conseil IA`).
- **Amélioration appliquée (E4)** : remplacement du libellé interne `Lot OctOpus` par `Précalcul périodique` dans le bloc *Sources des données*.

### 2.3 Exploitations (`/fr/exploitations`)
- **Visuel & Lisibilité** : 3 cartes KPI (`Exploitations`, `Parcelles`, `Surface totale` en `ha`) suivies du tableau récapitulatif (`Exploitation`, `Région`, `Commune`, `Surface (ha)`, `Parcelles`, lien `Voir les parcelles`).
- **États** : chargement, erreur et état vide (`Aucune exploitation.`) conformes.

### 2.4 Parcelles (`/fr/parcelles`)
- **Visuel & Filtres** : filtre par exploitation (`Toutes les exploitations`), compteur dynamique (`2 parcelles`), grille de cartes vivantes `FieldLiveCard` et accordéon `<details>` **Voir en tableau** pour une lecture tabulaire dense.

### 2.5 Détail Parcelle (`/fr/parcelles/[id]`)
- **Contenu** : fiche signalétique (`Surface`, `Sol`, `Irrigation`, `Culture` et date de semis), liens rapides (`Météo`, `Recommandations`), sélecteur de kit, carte **Dernière mesure** (`Humidité du sol`, `Température de l'air`, `Humidité de l'air`, horodatage), carte **Pompe** (état + rappel des sécurités matérielles), graphique **Humidité du sol** (`Jour`, `Semaine`, `Mois`, `Année`) et formulaire **Seuils d'irrigation** (`Démarrage (%)`, `Arrêt (%)` avec contrôle d'écart minimal).

### 2.6 Carte (`/fr/carte`)
- **Visuel & Leaflet** : canevas cartographique local sans dépendance à un serveur de tuiles externe (compatible hors-ligne et CSP stricte), sélecteur d'exploitation, boutons radio de coloration (`Humidité du sol`, `NDVI (vigueur)`, `Culture`, `Salinité`), cases à cocher (`Kits`, `Contours des parcelles`), légende dynamique, panneau latéral de la parcelle sélectionnée et **tableaux accessibles** sous la carte (`Parcelles de la carte`, `Kits de la carte`).

### 2.7 Météo (`/fr/meteo`)
- **Visuel & Données** : sélecteur de parcelle, capsule de fraîcheur (`Prévision à jour`, fournisseur `open-meteo`), bloc `Provenance`, carte météo immersive à 7 jours (`WeatherHero`), 4 KPI hebdomadaires (`Température max.`, `Température min.`, `Pluie cumulée`, `Évapotranspiration cumulée`) et 3 graphiques (`Températures`, `Pluie prévue`, `Évapotranspiration (ET0)`) chacun doté d'un bouton **Afficher le tableau des valeurs**.

### 2.8 Irrigation (`/fr/irrigation`)
- **Visuel & Données** : sélecteur de parcelle, carte `Besoin en eau à 24 h` (`Besoin aujourd'hui` en `mm`, `Volume recommandé` en `m³`, bandeau d'arrosage reporté si pluie attendue, lecture du résultat et bloc `Provenance` dépliable), suivie de la carte `Demande climatique sur 7 jours`.
- **Amélioration appliquée (E4)** : ajout du repère pratique *« Repère terrain : 1 mm d'eau équivaut à 1 L/m² (soit 10 m³ par hectare). »* pour faciliter la lecture immédiate par l'exploitant.

### 2.9 Fertilisation (`/fr/fertilisation`)
- **Visuel & Données** : sélecteur de parcelle, bandeau d'avertissement `Valeurs indicatives` (sonde NPK non étalonnée), 3 tuiles KPI (`Azote (N)`, `Phosphore (P)`, `Potassium (K)` en `kg/ha`), contexte cultural (`Culture`, `Stade`, `Classe NPK du sol`), phrase de synthèse et bloc `Provenance`.

### 2.10 Risques phytosanitaires (`/fr/risques`)
- **Visuel & Données** : sélecteur de parcelle, niveau de risque global (`Faible`, `Moyen`, `Élevé`), liste des ravageurs suivis (ex. *Thrips de l'oignon*) avec probabilités à 7 et 14 jours (ou mention explicite `probabilité non calibrée` conformément à Doc 16 § 6.3), facteurs favorables et bloc `Provenance`.

### 2.11 Assistant IA (`/fr/assistant`)
- **Visuel & Interactions** : journal de conversation `role="log" aria-live="polite"`, zone de saisie `Votre question` avec compteur `0 / 2000 caractères`, bouton de dictée vocale `Dicter ma question` (`VoiceInput`), bouton `Envoyer`, affichage des sources citées (`Citations`), bloc `Provenance` par réponse et bouton `Nouvelle conversation`.
- **Améliorations appliquées (E4)** :
  - Ajout de **3 suggestions de questions rapides** cliquables dans l'état initial (`Dois-je arroser demain ?`, `Quel est le risque de ravageurs sur mes parcelles ?`, `Comment interpréter les niveaux NPK de ma sonde ?`).
  - Alignement sur une même ligne de la commande vocale et du compteur de caractères.

### 2.12 Recommandations (`/fr/recommandations`)
- **Visuel & Interactions** : sélecteur de parcelle, bulle d'accueil du conseiller agronomique, cartes **Irrigation** (décision `Irriguer` / `Surveiller` / `Ne pas irriguer` / `Vérifier le capteur`, constat, dose nette/brute/volume, mise en garde) et **Fertilisation** (tableau `N`, `P`, `K` en `mg/kg` avec niveau `Bas` / `Moyen` / `Élevé`), provenance et boutons de retour exploitant (`Suivie`, `Suivie en partie`, `Pas suivie`, `Non applicable`).
- **Améliorations appliquées (E4)** :
  - Correction du badge moteur `Moteur vreco_engine@2` → **`Moteur v2`**.
  - Correction orthographique `Azote indicatif eleve.` → **`Azote indicatif élevé.`** (idem pour le phosphore).
  - Alignement horizontal de l'icône de bulle avec le motif du conseil.

### 2.13 Rapports (`/fr/rapports`)
- **Visuel & Interactions** : filtre de période (`Du` / `Au`) avec validation instantanée (`La date de début doit précéder la date de fin.`), bouton `Exporter` (CSV séparateur `;`), 8 tuiles KPI (`Parcelles`, `Kits`, `Disponibilité des kits`, `Mesures reçues`, `Arrosages`, `Heures de pompe`, `Eau consommée`, `Recommandations suivies`), et 2 tableaux (`Alertes par règle`, `Retours sur les recommandations`).
- **Améliorations appliquées (E4)** :
  - Traduction des identifiants techniques des règles d'alerte (`pump_fault` → `Défaut de pompe (pump_fault)`, `soil_dry` → `Sol sec (soil_dry)`, etc.).
  - Calibrage réaliste du débit des pompes solaires de démonstration (`10–12 m³/h`), rendant le cumul `Heures de pompe` physiquement cohérent sur 30 jours.

### 2.14 Équipements (`/fr/equipements`)
- **Visuel & Données** : 4 KPI (`Équipements`, `En service`, `En maintenance`, `Hors service`), bandeau de synthèse avec lien vers `/fr/kit`, tableau d'inventaire complet et section intégrée **Santé du kit** (`KitHealthSection` : état des 6 capteurs `Humidité du sol`, `Température et humidité de l'air`, `Capteur NPK`, `Débitmètre`, `Pompe`, `Batterie`).

### 2.15 Alertes (`/fr/alertes`)
- **Visuel & Interactions** : bandeau d'alerte critique ouverte, sélecteur de statut (`Ouvertes`, `Acquittées`, `Résolues`, `Toutes`), liste ordonnée `role="log"` avec gravité (`Critique`, `Avertissement`, `Information`), message, règle, provenance et bouton `Acquitter`.
- **Amélioration appliquée (E4)** : affichage du libellé français explicite de la règle d'alerte (`Règle Défaut de pompe (pump_fault)`).

### 2.16 Maladies (`/fr/maladies`)
- **Visuel & Interactions** : sélecteur de parcelle, sélecteur de fichier image (`JPEG, PNG ou WebP, 12 Mo au plus`), réduction côté client et retrait EXIF (`prepareImage.ts`), aperçu de la photo, bouton `Analyser la photo`, carte de verdict (`Plante saine`, `Maladie probable`, `Suspect`, `Incertain, faites vérifier` si confiance `< 70 %`), liste des hypothèses (`top3`) et bloc `Provenance`.
- **Amélioration appliquée (E4)** : ajout d'un conseil pratique de prise de vue (*« Conseil prise de vue : photographiez une feuille bien éclairée, de près et nette, sur fond simple. »*).

### 2.17 Campagnes (`/fr/campagnes`)
- **Visuel & Données** : cartes des campagnes agricoles avec statut (`En cours`, `Prévue`, `Close`), dates de début/fin, barre de progression accessible (`role="meter"`) et nombre de jours restants.
- **Amélioration appliquée (E4)** : traduction des codes de saison (`Saison dry` → **`Saison sèche (contre-saison)`**, `Saison rainy` → **`Saison des pluies (hivernage)`**).

### 2.18 Cultures (`/fr/cultures`)
- **Visuel & Interactions** : sélecteur de parcelle, filtre segmenté par état (`Tous`, `En cours`, `Prévus`, `Récoltés`, `Abandonnés`) avec compteurs, cartes de cycle cultural avec frise en 3 étapes (`Semis`, `Croissance`, `Récolte`) et affichage du rendement récolté.

### 2.19 Rendement (`/fr/rendement`)
- **Visuel & Données** : sélecteur de parcelle, badge `Expérimental`, 4 tuiles KPI (`Rendement prévu` en `t/ha`, `Intervalle probable`, `Rendement réel`, `Modèle`), graphique en barres (`Prudent`, `Attendu`, `Optimiste`) avec tableau des valeurs, note de précaution et bloc `Provenance`.
- **Amélioration appliquée (E4)** : francisation de la note de précaution (`validation croisée par saison sur peu de campagnes`).

### 2.20 Écrans complémentaires vérifiés (`/fr/kit`, `/fr/previsions`, `/fr/planning`, `/fr/pieges`, `/fr/vegetation`, `/fr/marches`)
- **Paramètres du kit (`/fr/kit`)** : santé des 6 capteurs + jeu de paramètres conseillés (`Seuils d'irrigation`, `Seuils d'alerte NPK`, `Étalonnage de la sonde d'humidité`, `Culture et stade`) et lien `Régler sur la parcelle`.
- **Humidité prévue (`/fr/previsions`)** : prévisions à `24 h`, `48 h` et `72 h` avec bande d'incertitude `p10–p90` et détection du passage sous le seuil de démarrage.
- **Planning d'arrosage (`/fr/planning`)** : sélecteur d'exploitation et de jour (`Aujourd'hui`, `Demain`), volume total, durée cumulée et tableau des créneaux horaires. **Amélioration appliquée (E4)** : affichage du nom lisible de la pompe (`Pompe solaire Ndiol`) au lieu de l'identifiant technique `eq-ndiol-pump` et durée cohérente avec la fenêtre horaire (`6 h`).
- **Pièges à insectes (`/fr/pieges`)** : comptages par période (`7`, `14`, `30 jours`), tendance et histogramme quotidien.
- **Végétation (`/fr/vegetation`)** : indices `NDVI` et `EVI`, couvert végétal (`%`), stade `BBCH` et part des relevés interpolés (nuages).
- **Prix du marché (`/fr/marches`)** : sélecteurs de culture et de marché, dernier prix observé (`FCFA/kg`), prévisions à 1–4 semaines et tableau d'écart. **Amélioration appliquée (E4)** : suppression de l'affichage `-0 %` par normalisation de `-0` vers `0` dans `changePct()`.
