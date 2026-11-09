# 00 — Lecture critique des documents d'entrée

Confidentiel — réservé aux partenaires de travail.

## 1. Documents analysés

| Document | Version | Contenu utile |
|---|---|---|
| `SmartAgri92_Dossier_Projet.pdf` (14 p.) | Cahier des charges v1.0, 19/10/2026 | Problème, objectifs, exigences F1–F13, NPK, architecture, composants, boîtier, câblage, logique d'arrosage, API locale, IA ESP-CAM, plan de tests, maintenance, risques, prochaines étapes |
| `SmartAgri92_firmware.ino` | v1.1 (issue de l'audit du 26/10/2026) | Point d'accès Wi-Fi par kit, `/data` en JSON, `POST /seuils` et `POST /plante` protégés par `X-Agri-Token`, sécurité pompe, CRC Modbus, `null` au lieu de `nan` |
| `SmartAgri92_Rapport_Audit_Securite.pdf` | 26/10/2026 | Constats et corrections du firmware, recommandations restantes (chiffrement flash, Secure Boot) |
| Prototype « Smart Agri92 — Tableau de bord du champ » | Exemple web fourni avec le brief OctOpus | Écran unique de suivi d'un champ ; analysé et repris en 13 modules dans `10_web_ux.md` |

En attente : le second document annoncé (si ce n'est pas le firmware) et le règlement et les données de la compétition. Les points qui en dépendent sont signalés « EN ATTENTE » dans ce dossier.

## 2. Ce qui est solide

- Positionnement juste : l'outil aide à décider mais ne remplace pas l'agriculteur. C'est aussi ce qui protège juridiquement le projet en cas de mauvaise récolte.
- Le fonctionnement hors ligne (F11) est une exigence essentielle, et c'est bien le cas : c'est la réalité du terrain au Sénégal.
- Matériel modulaire et réparable, connecteurs à brancher en un geste : c'est ce qui fera tenir le kit sur plusieurs saisons.
- Le plan de tests est concret et vérifiable (air, eau, terre ; 10 minutes ; redémarrage).
- Le dossier dit lui-même qu'il faut un seuil de confiance et plusieurs détections avant d'alerter. Cette lucidité sur l'IA est rare dans un dossier de prototype.

## 3. Manques et incohérences (par ordre de priorité)

| # | Constat | Conséquence | Proposition | Priorité |
|---|---|---|---|---|
| L1 | Le kit ne garde **aucun historique** et **n'a pas d'horloge** | Les courbes jour/semaine/mois/année (F9) sont impossibles hors ligne, et les données sans horodatage ne valent rien pour l'IA | Firmware v1.2 : tampon circulaire LittleFS d'agrégats sur 5 min (environ 30 jours), route `GET /historique?depuis=`, heure fournie par le téléphone à chaque connexion (et SNTP quand il y a Internet) | Bloquant |
| L2 | **Aucun chemin vers le cloud** n'est défini : le kit n'est qu'un point d'accès local | « Connecter le kit au site web » (§17) n'a pas de solution technique | Trois voies, combinables : (a) le téléphone sert de relais différé ; (b) le kit se connecte en Wi-Fi client sur un routeur 4G de la coopérative et publie en MQTT ; (c) passerelle LoRaWAN de coopérative (V3). Voir `02_architecture.md` | Bloquant |
| L3 | L'application doit appeler `http://192.168.4.1` | Un site web ou une PWA servis en HTTPS ne peuvent pas appeler une adresse HTTP locale (contenu mixte bloqué par le navigateur) | **Application native** (Flutter) pour tout ce qui parle au kit ; le site web sert au suivi à distance | Bloquant |
| L4 | Arrosage par **seuils fixes** | Ne tient compte ni du stade de la culture, ni de la chaleur, ni de la pluie annoncée : risque de gaspillage ou de stress hydrique | Garder les seuils sur le kit comme **filet de sécurité** et ajouter côté plateforme une recommandation ET0 FAO-56 × Kc + bilan hydrique + prévision de pluie | Haute |
| L5 | **Pas de capteur de niveau d'eau ni de débit** (le dossier le mentionne en §16) | La pompe peut tourner à sec (dégât matériel) et on ne peut pas mesurer l'eau économisée, qui est le premier argument de vente | Flotteur de cuve (environ 1 000 FCFA) sur une entrée libre, puis débitmètre à effet Hall (type YF-S201) | Haute |
| L6 | Capteurs **NPK RS485 bon marché** | Ces sondes estiment N, P et K à partir de la conductivité : la valeur varie avec l'humidité et la température et ne vaut pas une analyse de laboratoire | Afficher des **niveaux** (bas / moyen / élevé), jamais de dose. Calibrer par type de sol avec un modèle ML entraîné sur des analyses de laboratoire (voir `03_ia.md`, cas IA-6) | Haute |
| L7 | **Seuils NPK par culture** non définis (F5) | L'alerte engrais n'a pas de référence | Tables par culture et par type de sol à construire avec un agronome (ISRA, ANCAR, CDH) ; versionnées dans la plateforme | Haute |
| L8 | **Budget énergétique** non chiffré (F12) | Batterie et panneau risquent d'être sous-dimensionnés, avec un kit éteint en saison des pluies | Mesurer avec un wattmètre USB. Ordre de grandeur à vérifier : ESP32-S3 en point d'accès et écran TFT allumé, environ 1 W en continu, soit environ 24 Wh/jour. Mise en veille de l'écran, panneau de 20 W et batterie d'au moins 50 Wh. La pompe a sa propre alimentation | Haute |
| L9 | `/plante` reçoit seulement 0 ou 1 ; le dossier parle de sain / suspect / malade | Information perdue (classe, confiance, image) ; aucune trace de la culture | v1.2 : `POST /plante` avec un corps JSON `{etat: 0\|1\|2, confiance, classe, image_id}`. Le verdict détaillé part vers la plateforme (`/v1/diagnoses`) | Moyenne |
| L10 | **Caméra fixe** ESP32-CAM (ESP32 classique, mémoire limitée) | Elle ne voit que quelques plantes, avec une lumière très variable ; un classifieur embarqué y reste rudimentaire | Approche double : photos prises par l'agriculteur avec son téléphone (diagnostic principal) et caméra fixe comme sentinelle (changement de couleur, flétrissement). Voir `03_ia.md`, cas IA-3 | Moyenne |
| L11 | **Comptes utilisateurs** par identifiant et mot de passe (F10) | Mots de passe oubliés, partagés, notés sur papier, pour un public parfois peu à l'aise avec l'écrit | Connexion par **numéro de téléphone + code à usage unique (SMS ou WhatsApp)** pour les agriculteurs ; mot de passe + second facteur pour le personnel et les conseillers | Moyenne |
| L12 | Aucune **mise à jour à distance** du firmware | Une faille ou un bogue oblige à se déplacer pour chaque kit | OTA signée (partition A/B, rollback), d'abord via l'application, puis en MQTT | Moyenne |
| L13 | Protection anti-copie par la **discrétion** (site sans détails techniques) | Ne protège pas vraiment : le boîtier s'ouvre et le firmware se lit | La vraie barrière, ce sont les données, les modèles calibrés localement, le réseau de coopératives et le service. Côté matériel : chiffrement flash + Secure Boot en production (irréversible, à planifier avec l'industrialisation) | Moyenne |
| L14 | **Modèle économique** absent | Impossible de dimensionner la feuille de route et le budget | Hypothèses à tester : kit à 90–120 kFCFA (estimation), location ou paiement échelonné via Wave / Orange Money, achat par la coopérative, offres B2B (exportateurs, assureurs, ONG). Voir `01_analyse_metier.md` | Haute |
| L15 | Interface **en français uniquement** | Elle exclut une partie des agriculteurs | Interface fr, wolof et pulaar, avec pictogrammes, couleurs et messages vocaux ; traductions validées par des locuteurs natifs | Moyenne |
| L16 | Test terrain de **7 jours** seulement | Trop court pour mesurer l'impact (eau, rendement) ou la robustesse en saison des pluies | Pilote d'une saison complète avec des parcelles témoins, en mesurant l'eau consommée, le rendement et les pannes | Haute |
| L17 | **Données personnelles** non traitées (téléphones, position des parcelles, photos) | Obligations de la loi 2008-12 et déclaration à la CDP | Registre des traitements, consentement, hébergement et transferts documentés, droits d'accès et d'effacement. Voir `06_devsecops.md` | Haute |
| L18 | Tableau des rôles vide (§17) | Personne n'est responsable de quoi que ce soit | Équipe proposée dans `07_feuille_de_route_budget.md` | Haute |
| L19 | Étalonnage du capteur sol en deux points, air et eau | Dans les sols sableux des Niayes, la courbe réelle s'écarte du linéaire | Étalonnage sur le sol de la parcelle (pesée sol sec / sol saturé), avec des profils d'étalonnage par type de sol dans la plateforme | Moyenne |
| L20 | Firmware v1.1 **ni compilé ni testé** sur le matériel | Toute la plateforme s'appuie sur son API | Compiler, puis dérouler le plan de tests du rapport d'audit **avant** le pilote | Bloquant |

## 4. Améliorations proposées au-delà des documents

1. **Le téléphone comme relais différé** : à chaque visite de la parcelle, l'application récupère l'historique du kit, le garde dans une file locale et l'envoie dès qu'il y a du réseau. C'est ce qui rend le service utile sans abonnement de données pour le kit.
2. **Les alertes passent par WhatsApp et SMS**, pas seulement par l'écran du kit : l'agriculteur n'est pas toujours au champ. Le dossier prévoit déjà l'aide par WhatsApp.
3. **Un conseiller dans la boucle** : dans les cas sensibles (maladie, traitement), l'assistant transmet la demande à un conseiller humain au lieu de répondre seul.
4. **Mesurer l'impact** : l'eau économisée et les pertes évitées sont les chiffres qui convaincront les bailleurs, les coopératives et les assureurs. Il faut un débitmètre (L5) et des parcelles témoins (L16).
5. **Commencer par un segment** : le maraîchage irrigué des Niayes (forte valeur, eau coûteuse, sols sableux, filières d'export), avant le riz de la vallée du fleuve ou les cultures pluviales.
6. **Tenir un registre des données d'entraînement** : chaque photo garde son consentement, sa culture, son stade, le diagnostic de l'agronome et la parcelle. C'est l'actif le plus difficile à copier.

## 5. Comment lire la suite

- Chaque recommandation technique distingue trois variantes : **(1) optimale pour gagner la compétition**, **(2) optimale pour la production**, **(3) compromis réaliste**. Le règlement de la compétition n'est pas encore connu. Pour les choix logiciels et d'infrastructure, la variante « compétition » désigne donc ce qui maximise la démonstration et le score en un temps limité.
- Ce qui a été réellement exécuté (tests, scripts, rendus) et ce qui ne l'a pas été est dit explicitement dans `README.md`.
