# 48 — Protocole de Déploiement Terrain des Premiers Kits (`IA-REAL-04`)

**Date** : 16 novembre 2026  
**Statut** : Procédure standardisée tout-Sénégal (14 régions) — *Confidentiel — réservé aux partenaires de travail.*  
**Objectif** : Garantir que tout kit installé n'importe où au Sénégal produise des mesures propres, géolocalisées, étalonnées et exploitables dès le Jour 1.

---

## 1. Pré-provisioning en atelier (avant départ sur le terrain)

Chaque kit portant un numéro de série unique `SA92-XXXXXX` doit passer 5 vérifications en atelier :
1. **Identité & Clé** : flasher le certificat/identifiant MQTT ou la clé `X-Device-Key` unique ; vérifier que le boîtier est `active` dans `devices`.
2. **Horloge & Fuseau** : vérifier la synchronisation NTP / RTC UTC (toute dérive supérieure à `+10 min` dans le futur entraîne le rejet des points par `ts_plausible()`).
3. **Test capteurs sur banc** : vérifier `soil_sensor_ok = true`, `bme_ok = true`, `npk_ok = true`, `pump_fault = false`, tension batterie `>= 3700 mV` et lecture des seuils initiaux (`seuilStart + 5 <= seuilStop`).
4. **Carte SIM & APN** : valider l'accroche réseau GSM/LTE et la mise en tampon local (carte SD / flash) en cas de perte de couverture.
5. **Fiche matériel** : noter l'identifiant du kit, le modèle de sonde, le débit nominal de la pompe (si connu) et le type d'irrigation (`drip`, `sprinkler`, `furrow`, `manual`).

---

## 2. Installation physique sur parcelle (n'importe où au Sénégal)

### 2.1 Choix de l'emplacement représentatif
- Installer le boîtier dans une **zone homogène et représentative** de la culture irriguée (éviter les bordures de parcelle, les cuvettes d'eau stagnante ou les zones piétinées).
- En irrigation **goutte-à-goutte**, placer la sonde capacitive à **15–20 cm de l'émetteur (goutteur)** dans le bulbe humide actif, et non en sol sec entre deux lignes.
- Orienter le panneau solaire **plein Sud** (inclinaison ~15° adaptée à la latitude du Sénégal `12°–17°N`), dégagé de tout ombrage d'arbre ou de culture haute.

### 2.2 Pose des capteurs
1. **Sonde capacitive d'humidité du sol** :
   - Enfoncer verticalement ou à 45° à **$-20\text{ cm}$ de profondeur** (zone racinaire maraîchère active).
   - **Zéro poche d'air** : tasser délicatement la terre humide autour de la lame de mesure ; l'air autour de la sonde fausse la permittivité diélectrique et fait chuter la mesure vers `0–5 %`.
2. **Capteur BME280 (T° / HR / Pression)** :
   - Sous abri ventilé blanc à **1,5 m** du sol (jamais en plein soleil ni enfermé dans le boîtier étanche IP65).
3. **Sonde NPK (RS485)** :
   - Insérée au même horizon racinaire (`10–20 cm`), en rappelant au producteur que ses valeurs sont **indicatives** (dépendantes de la conductivité et de l'humidité) et ne remplacent pas une analyse de laboratoire (`agronomy.py`).
4. **Câblage & Étanchéité** :
   - Boucles d'égouttement sur chaque câble entrant par presse-étoupe en face inférieure du boîtier.

---

## 3. Enrôlement numérique & Rattachement au Data Lake National

Sur place, via l'interface ou l'outil technicien :
1. **Enregistrer les coordonnées GPS exactes `(lat, lon)`** du centroïde de la parcelle (précision téléphone `< 10 m`), sa surface (`area_ha`), la culture et la date de semis/repiquage.
2. **Rattachement automatique** : ces coordonnées positionnent immédiatement la parcelle sur la grille nationale `0,05°` (`cell_id`, `power_cell_id`) sans aucune saisie manuelle de zone pilote.
3. **Configuration initiale des seuils** : régler `threshold_start_pct` et `threshold_stop_pct` en cohérence avec la texture locale issue de `isdasoil_national_grid_0p05.parquet` (ex. sol sableux *dior* vs sol argileux *hollaldé*) tout en respectant `0 <= start`, `start + 5 <= stop <= 100`.

---

## 4. Protocole d'étalonnage gravimétrique à la pose (`sm_calibration`)

La lecture capacitive brute variant selon la texture et la salinité du sol, prélever **au minimum 2 échantillons de sol** à $-20\text{ cm}$ juste à côté de la sonde lors de l'installation (et répéter après un arrosage) :
1. Relever l'horodatage UTC exact et la valeur `soil_moisture_pct` affichée par le kit au moment du prélèvement.
2. Prélever ~100 g de sol intact dans une boîte hermétique tarée, peser immédiatement le **poids humide ($M_h$)**.
3. Sécher à l'étuve à **105 °C pendant 24 h** au laboratoire partenaire, puis peser le **poids sec ($M_s$)** pour obtenir l'humidité gravimétrique réelle $w = (M_h - M_s) / M_s$.
4. Associer cette mesure dans le futur jeu `sols.lab_results` afin de calibrer la courbe de transfert spécifique à chaque type de sol sénégalais.

---

## 5. Protocole de recette Jour 1 (15 minutes avant de quitter la parcelle)

Le technicien ne quitte la parcelle qu'après validation des **6 points suivants** :
1. **Réception serveur confirmée** : au moins **3 paquets consécutifs** visibles côté Backend (`last_seen_at` < 15 min, `source = 'mqtt'` ou `'http'`).
2. **Santé capteurs au vert** : `GET /v1/devices/{id}/health` retourne `state = "ok"` sur `soil`, `bme`, `npk`, `pump`, `battery` (`flow` peut être `"absent"` sur kit v1.1 sans débitmètre).
3. **Plausibilité physique immédiate** : `air_temp_c` cohérente avec l'ambiant (`15–45 °C`), `pressure_hpa` proche de `1005–1020 hPa`, `soil_moisture_pct` non figé à `0 %` ou `100 %`.
4. **Test actionneur pompe** : un déclenchement manuel court confirme le basculement `pump_on: false -> true -> false` sans `pump_fault: true`.
5. **Synchronisation des seuils** : `reported_start_pct == desired_start_pct` et `reported_stop_pct == desired_stop_pct` (`sync_status = "synced"`).
6. **Formation express du producteur** : expliquer la lecture des voyants, le nettoyage du panneau solaire (poussière/harmattan) et la consigne de ne jamais déplacer la sonde sans prévenir le technicien.
