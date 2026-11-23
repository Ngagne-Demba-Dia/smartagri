# Catalogue data et IA de SmartAgri92

> Document confidentiel, réservé aux partenaires de travail. Ne pas diffuser.

Ce dossier est la **source de vérité** de l'inventaire des données et de la cartographie des modèles (brief IA, Data et MLOps du 27/10/2026). Trois fichiers YAML décrivent la chaîne complète :

```
sources.yaml   (104 sources)    →   datasets.yaml   (110 jeux)    →   models.yaml   (39 modèles)
 d'où vient la donnée               raw → curated → features            ce qui la consomme
```

Un validateur (`agriml.catalog`) contrôle la forme de chaque entrée et neuf règles de cohérence entre les fichiers. Les annexes A1–A4 de `docs/annexes/` sont **générées** à partir du catalogue. Les documents 13 à 16 les commentent sans les recopier.

## Commandes

Elles se lancent depuis `ml/`, avec `PYTHONPATH=src` si le paquet n'est pas installé.

| Commande | Effet |
|---|---|
| `python -m agriml.catalog check` | Valide le schéma et les neuf règles. Affiche erreurs et avertissements, puis un bilan. |
| `python -m agriml.catalog check --strict` | Comme `check`, mais les avertissements font aussi échouer la commande. |
| `python -m agriml.catalog render [--out DIR]` | Régénère les annexes A1–A4 (par défaut `docs/annexes/`). |
| `python -m agriml.catalog render --check` | N'écrit rien. Échoue si une annexe diffère du rendu. |
| `python -m agriml.catalog lineage <modèle>` | Liste les jeux et les sources en amont d'un modèle, par niveau de nécessité. |
| `--dir DIR` (option globale) | Lit un autre catalogue. Sinon : variable `AGRIML_CATALOG_DIR`, puis `ml/catalog`. |

**Codes de sortie**

| Code | Sens |
|---|---|
| 0 | Catalogue conforme. Les avertissements sont tolérés sans `--strict`. |
| 1 | Erreurs ; ou avertissements avec `--strict` ; ou annexes périmées avec `render --check` ; ou `render` sur un catalogue en erreur (rien n'est écrit). |
| 2 | Catalogue illisible (YAML invalide, champ inconnu ou manquant, valeur hors énumération) ou modèle inconnu pour `lineage`. |

**État au 02/11/2026** : `check` sort en 0, avec 0 erreur et 49 avertissements (35 `licence.pending`, 14 `octopus.licence`). `check --strict` sort donc en 1, ce qui est attendu tant que les licences ne sont pas confirmées. La liste des licences à confirmer est le point de départ du doc 15.

## Procédure de modification

1. Modifier le YAML. Les identifiants ne se renomment pas sans mettre à jour toutes les références.
2. `python -m agriml.catalog check` : corriger toutes les erreurs.
3. `python -m agriml.catalog render` : régénérer les annexes. Ne jamais les éditer à la main.
4. `pytest tests/test_catalog.py` : le test `test_repository_annexes_are_up_to_date` échoue si l'étape 3 a été oubliée.
5. Si un fait change dans une annexe (licence, coût, disponibilité), vérifier le passage correspondant des docs 13 à 16.

## Champs

Les commentaires d'en-tête de chaque fichier YAML rappellent ces champs. Un champ inconnu est une erreur : une faute de frappe ne passe pas inaperçue.

### `sources.yaml`

| Champ | Obligatoire | Valeurs |
|---|---|---|
| `id` | oui | identifiant unique, en snake_case |
| `domain` | oui | `meteo`, `sols`, `satellite`, `drone`, `iot`, `phyto`, `agronomie`, `economie`, `geo`, `eau`, `historique`, `utilisateurs`, `langue`, `connaissances` |
| `kind` | oui | `public_api`, `open_data`, `commercial`, `partner`, `internal`, `user_input`, `reference`, `pretrained` |
| `name`, `licence` | oui | texte |
| `commercial` | oui | `open` (usage commercial permis) · `contract` (accord, abonnement ou conditions à signer) · `restricted` (non commercial seulement) · `unknown` (licence non confirmée) |
| `personal` | oui | `none` · `indirect` (rattachée à une parcelle ou à un kit) · `direct` (identifie une personne) |
| `coverage` | oui | couverture du Sénégal : `full`, `partial`, `none`, `unknown` |
| `identifying` | non | `true` si le contenu identifie la personne même après minimisation (voix). Défaut : `false`. |
| `verified` | non | date `"AAAA-MM-JJ"` (entre guillemets) de la dernière lecture de la licence sur une page publique, sinon `null` |
| `evidence` | non | URL lue lors de la vérification |
| `cost`, `access`, `details` | non | texte libre ; « hypothèse » signale un chiffre à valider par devis |

Une source `verified` peut rester `unknown` si la page publique ne tranche pas. Le champ indique ce qui a été lu, pas une conclusion juridique.

### `datasets.yaml`

| Champ | Obligatoire | Valeurs |
|---|---|---|
| `id` | oui | préfixé par la zone ou le domaine (`raw.iot.telemetry`, `meteo.forecast_asof`, `features.irrigation_need`) |
| `zone` | oui | `raw` (immuable ; entrées = sources) · `curated` (entrées = raw ou curated) · `features` (entrées = curated ou features) |
| `domain` | oui | mêmes valeurs que pour les sources |
| `available` | oui | première version où le jeu existe : `MVP`, `V1.1`, `V2`, `V3` |
| `classification` | oui | `publique`, `interne`, `confidentielle`, `personnelle` |
| `inputs` | oui | identifiants des sources (zone raw) ou des jeux (autres zones) |
| `content` | oui | ce que contient le jeu |
| `grain`, `refresh`, `volume`, `retention` | non | texte ; le volume donne son calcul (hypothèse : 10 000 kits et 20 000 parcelles en cible, 100 kits en pilote) |
| `minimised` | non | pseudonymisation, coordonnées arrondies, champs libres retirés : abaisse `direct` en `indirect` |
| `aggregated` | non | agrégation k-anonyme (k ≥ 10 exploitations par cellule) : abaisse le niveau à `none` |
| `research_only` | non | jeu soumis à une licence non commerciale |
| `holdout` | non | un holdout est gardé dans `curated/holdout/<jeu>/` et n'est jamais exporté |
| `octopus` | non | `{policy, name, licence_cleared}` ; `policy` vaut `forbidden` (défaut), `public` ou `pseudonymised` |

Le niveau de donnée personnelle d'un jeu **n'est pas déclaré**. Il est calculé à partir des sources amont (règle 3), ce qui évite qu'une jointure fasse disparaître une donnée personnelle sans que personne le remarque.

### `models.yaml`

| Champ | Obligatoire | Valeurs |
|---|---|---|
| `id`, `name` | oui | identifiant unique, libellé |
| `use_case` | oui | `IA-1` à `IA-10` (cas d'usage du doc 04) ou `TRANSVERSE` |
| `kind` | oui | nature de la variante production : `rules`, `physical`, `statistics`, `ml`, `deep_learning`, `llm`, `optimisation` |
| `version` | oui | première version livrée : `MVP`, `V1.1`, `V2`, `V3` |
| `platform` | oui | liste parmi `web:N` (module web 1 à 13, doc 10 §3), `mobile`, `kit`, `partner` |
| `data` | oui | `mandatory` (au moins un jeu), `recommended`, `optional` : jeux curated ou features, jamais raw |
| `candidates` | oui | exactement `competition`, `production` et `compromis` |
| `metrics` | oui | `primary`, `threshold` (seuil d'acceptation), `secondary` (liste) |
| `training` | oui | protocole d'entraînement et de validation |
| `inference` | oui | `mode` (`batch`, `online`, `edge`, `stream`), `fallback` (obligatoire), `latency`, `frequency` |
| `features` | non | variables explicatives principales |
| `pretrained` | non | sources `pretrained` utilisées en production |
| `pretrained_research` | non | sources `pretrained` utilisées en recherche seulement (licence non commerciale) |
| `depends_on` | non | modèles amont |
| `octopus_program` | non | programme de `agriml/octopus/programs/` dont le jeu doit être obligatoire pour ce modèle |
| `challenge` | non | limite ou risque principal |

## Les neuf règles

Toutes produisent une **erreur**, sauf celles marquées *avertissement*. Le code entre parenthèses est celui affiché par `check`.

1. **Références** :
   - tout identifiant cité existe (`ref.unknown`) ;
   - les zones s'enchaînent dans le bon sens, et un modèle ne lit jamais un jeu raw (`ref.zone`) ;
   - un même jeu n'est cité qu'à un seul niveau dans un modèle (`ref.level`) ;
   - `pretrained` et `pretrained_research` désignent des sources de type `pretrained` (`ref.pretrained`) ;
   - un modèle ne dépend pas d'un modèle livré après lui (`availability.depends_on`) ;
   - les dépendances entre modèles sont sans cycle (`graph.model_cycle`).

   `ref.level` est une erreur, et non un avertissement : un jeu cité à deux niveaux rend la lignée ambiguë.
2. **Graphe des jeux sans cycle** (`graph.cycle`). Les calculs transitifs (règle 3, `lineage`) refusent un graphe cyclique.
3. **Donnée personnelle** (`personal.classification`) :
   - le niveau d'un jeu est le maximum de son amont ;
   - `minimised` abaisse `direct` en `indirect`, et `aggregated` abaisse le niveau à `none` ;
   - un contenu `identifying` (la voix) n'est jamais abaissé ;
   - la classification doit être au moins `confidentielle` pour `indirect` et `personnelle` pour `direct`.
4. **Politique OctOpus** :
   - un jeu raw ou identifiant n'est jamais exporté (`octopus.policy`) ;
   - `public` exige l'absence de donnée personnelle et une classification publique ou interne ;
   - `pseudonymised` exige la zone features, un niveau au plus `indirect` et `holdout: true` ;
   - chaque nom OctOpus est unique (`octopus.name`) ;
   - une source `restricted` en amont interdit l'export (`octopus.licence`) ;
   - une source `contract` ou `unknown` en amont produit un *avertissement* `octopus.licence`, tant que `licence_cleared: true` n'est pas posé.
5. **Licences** :
   - un jeu dont l'amont est non commercial doit déclarer `research_only` (`licence.research_only`) ;
   - un jeu `research_only` n'est admis qu'en `optional` dans un modèle (`licence.research_only`) ;
   - un modèle pré-entraîné non commercial va dans `pretrained_research` (`licence.pretrained`) ;
   - *avertissement* `licence.pending` : une source `contract` ou `unknown` est obligatoire ou recommandée pour au moins un modèle.
6. **Disponibilité** :
   - un jeu n'existe pas avant ses entrées (`availability.dataset`) ;
   - un modèle n'est pas livré avant ses jeux obligatoires (`availability.model`).
7. **Programmes OctOpus** (fichiers de `agriml/octopus/programs/`, hors `competition*`) :
   - le jeu du programme est un jeu features exportable du catalogue (`program.dataset`) ;
   - l'espace de travail est cohérent : `agri92-sandbox` pour `public`, `agri92-pilot` ou `agri92-prod` pour `pseudonymised` (`program.workspace`) ;
   - le `octopus_program` d'un modèle existe (`program.unknown`) et son jeu est obligatoire pour ce modèle (`program.dataset`) ;
   - *avertissement* `program.unused` : programme repris par aucun modèle.
8. **Inutilisés** (*avertissements* `unused.source`, `unused.dataset`) : une source ou un jeu que rien ne lit.
9. **Identifiants uniques** (`duplicate_id`), sur l'ensemble des trois fichiers.

## Exception de taille

Les règles du projet fixent un plafond indicatif de 800 lignes par fichier source. `models.yaml` le dépasse (986 lignes) délibérément :
- c'est un fichier de **données**, pas du code ;
- chaque modèle y occupe environ 25 lignes lisibles, une par champ ;
- le découper par cas d'usage multiplierait les fichiers sans rien rendre plus lisible, et le validateur devrait alors fusionner les morceaux.

Le code du validateur reste sous le plafond : 452 lignes au plus (`rules.py`).

## Ce que le catalogue ne garantit pas

- **Les licences** : `commercial` reflète la lecture d'une page publique à la date `verified`. Ce n'est pas un avis juridique. Les sources à `verified: null` n'ont pas été relues.
- **Les volumes et les coûts** sont des hypothèses de dimensionnement. Ils sont à confronter aux devis et aux mesures du pilote.
- **La pertinence d'un modèle** : le catalogue vérifie que ses données existent et sont utilisables, pas qu'il atteindra son seuil.
