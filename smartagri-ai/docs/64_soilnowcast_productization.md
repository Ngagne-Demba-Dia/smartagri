# 64 — SoilNowcast Productization Guide

> **SmartAgri92 — Actif IA transferable et commercialisable**
> Ce document formalise le passage du prototype SoilNowcast
> vers un actif logiciel exploitable dans le produit SmartAgri.

---
## 1. Modele retenu : LightGBM

### 1.1 Comparaison finale

| Critere | LightGBM | XGBoost | CatBoost |
|---|---|---|---|
| J+1 | RMSE=7.405, R2=0.8375 **champion** | RMSE=7.492, R2=0.8324 | RMSE=7.619, R2=0.8307 |
| J+2 | RMSE=7.411, R2=0.8369 **champion** | RMSE=7.458, R2=0.8337 | RMSE=7.553, R2=0.8353 |
| J+3 | RMSE=7.525, R2=0.8314 **champion** | RMSE=7.532, R2=0.8308 | RMSE=7.712, R2=0.8273 |
| CV% folds | 19.1% | 20.4% | 16.4% |
| Taille modele | ~3.8 Mo/fold | ~3.5 Mo/fold | ~240 Ko/fold |
| Export ONNX | natif | natif | natif |
| Inference (ms/batch 1K) | ~2 ms | ~3 ms | ~5 ms |

### 1.2 Verdict

**LightGBM est le champion global** (RMSE moyen = 7.447).

Raisons du choix :
1. Meilleur RMSE sur J+1 et J+2.
2. Inference la plus rapide (~2 ms / batch de 1000 lignes).
3. Export natif : `.txt` (lisible humain) + ONNX + pickle.
4. Ecosysteme mature : SHAP, ONNX Runtime, LightGBM C API.
5. CatBoost en backup pour la meilleure stabilite inter-folds.

> **Production** : deployer les 5 folds LightGBM en ensemble.
> Conserver les 5 folds CatBoost comme fallback.

---
## 2. Hyperparametres definitifs

### 2.1 LightGBM (champion)

```yaml
hyperparameters:
  colsample_bytree: 0.8
  learning_rate: 0.05
  max_depth: 8
  min_child_samples: 50
  n_estimators: 800
  n_jobs: 2
  num_leaves: 63
  random_state: 42
  reg_alpha: 0.1
  reg_lambda: 1.0
  subsample: 0.8
  verbose: -1
early_stopping: 50
seed: 42
n_folds: 5
group: power_cell_id
validation: GroupKFold
```

### 2.2 CatBoost (backup)

```yaml
  colsample_bylevel: 0.8
  depth: 7
  early_stopping_rounds: 30
  iterations: 300
  l2_leaf_reg: 3.0
  learning_rate: 0.08
  loss_function: RMSE
  random_seed: 42
  subsample: 0.8
  thread_count: 2
  verbose: 0
```

### 2.3 XGBoost (reference)

```yaml
  colsample_bytree: 0.8
  early_stopping_rounds: 50
  eval_metric: rmse
  learning_rate: 0.05
  max_depth: 8
  min_child_weight: 50
  n_estimators: 800
  n_jobs: 2
  random_state: 42
  reg_alpha: 0.1
  reg_lambda: 1.0
  subsample: 0.8
  tree_method: hist
```

---
## 3. Features retenues et rejetees

### Tier 1 — Critiques (SHAP >= 2.0)

| Feature | SHAP moyen | Domaine | Role |
|---|---|---|---|
| `et0_pm_mean_7d_mm` | **6.746** | Evapotranspiration | Demande evaporative moyenne 7j |
| `ph_h2o` | **3.716** | Sol | Acidite du sol, retention hydrique |
| `soc_g_kg` | **2.644** | Sol | Carbone organique, porosite |
| `doy_sin` | **2.427** | Temporel | Saisonnalite sinusoidale |
| `share_tree` | **2.315** | Occupation | Couvert arbore, ombre + infiltration |
| `rain_nasa_sum_14d_mm` | **2.208** | Pluie | Cumul NASA 14j, recharge profonde |
| `rh_mean_pct` | **2.173** | Meteo | Humidite relative, evaporation |

### Tier 2 — Importantes (0.5 <= SHAP < 2.0)

| Feature | SHAP moyen | Domaine | Role |
|---|---|---|---|
| `et0_pm_mm` | 1.270 | Evapotranspiration | ET0 Penman-Monteith journaliere |
| `doy_cos` | 0.762 | Temporel | Saisonnalite cosinusoidale |
| `share_crop` | 0.695 | Occupation | Part cultures, irrigation/drainage |
| `sand_pct` | 0.633 | Sol | Sable, drainage rapide |
| `clay_pct` | 0.631 | Sol | Argile, retention |
| `bulk_density_g_cm3` | 0.518 | Sol | Densite, compaction |
| `t_min_c` | 0.516 | Meteo | Temperature minimale, rosee |
| `share_bare` | 0.510 | Occupation | Sol nu, evaporation directe |

### Tier 3 — Support (SHAP < 0.5)

| Feature | SHAP moyen | Domaine | Role |
|---|---|---|---|
| `wp_ptf_pct` | 0.463 | Sol | Point de fletrissement |
| `solar_rad_mj_m2` | 0.380 | Meteo | Radiation solaire |
| `pressure_hpa` | 0.376 | Meteo | Pression atmospherique |
| `share_built` | 0.370 | Occupation | Bati, impermeabilisation |
| `t_max_c` | 0.360 | Meteo | Temperature max, stress |
| `rain_chirps_sum_7d_mm` | 0.326 | Pluie | Cumul CHIRPS 7j |
| `wind_2m_ms` | 0.309 | Meteo | Vent, evaporation |
| `rain_chirps_sum_14d_mm` | 0.202 | Pluie | Cumul CHIRPS 14j |
| `rain_nasa_sum_7d_mm` | 0.191 | Pluie | Cumul NASA 7j |
| `fc_ptf_pct` | 0.183 | Sol | Capacite au champ PTF |
| `t_mean_c` | 0.152 | Meteo | Temperature moyenne |
| `rain_mm` | 0.147 | Pluie | Pluie jour J NASA |
| `rain_nasa_sum_3d_mm` | 0.145 | Pluie | Cumul NASA 3j |
| `rain_chirps_mm` | 0.108 | Pluie | Pluie jour J CHIRPS |
| `rain_chirps_sum_3d_mm` | 0.057 | Pluie | Cumul CHIRPS 3j |

### Features rejetees

| Feature | Raison |
|---|---|
| `soil_wetness_root_pct` | Absente du test. Etat J+0, indisponible en inference. V2 avec tensiometres pourra l'utiliser. |
| `power_cell_id` | Identifiant de groupe pour GroupKFold. |
| `ts` | Timestamp, encode via doy_sin/doy_cos. |

---
## 4. Artefacts a exporter

| # | Artefact | Format | Taille | Usage |
|---|---|---|---|---|
| 1 | lgb_xgb_models.zip | ZIP | 55.5 Mo | 15 LGB .txt + 15 XGB .json |
| 2 | cb_models.zip | ZIP | 3.5 Mo | 15 CatBoost .cbm |
| 3 | config_all.json | JSON | 1.8 Ko | Hyperparametres reproductibles |
| 4 | soilnowcast_all_metrics.csv | CSV | 2.5 Ko | 45 metriques |
| 5 | soilnowcast_feature_importance_all.csv | CSV | 1.0 Ko | Importance 3 algos |
| 6 | soilnowcast_group_errors.csv | CSV | 45.8 Ko | Erreurs par cellule |
| 7 | shap_values_summary.csv | CSV | 1.3 Ko | SHAP par feature x horizon |
| 8 | soilnowcast_oof.parquet | Parquet | 18.5 Mo | 258K predictions OOF |
| 9 | shap_summary.png | PNG | 112 Ko | Visualisation SHAP |
| 10 | fold_stability.png | PNG | 71 Ko | Stabilite inter-folds |
| 11 | group_errors_plot.png | PNG | 60 Ko | Erreurs par groupe |

### Export ONNX

```python
import lightgbm as lgb
from onnxmltools import convert_lightgbm
from onnxmltools.convert.common.data_types import FloatTensorType
FEATURES = ["bulk_density_g_cm3", "clay_pct", "doy_cos", "doy_sin", "et0_pm_mean_7d_mm", "et0_pm_mm", "fc_ptf_pct", "ph_h2o", "pressure_hpa", "rain_chirps_mm", "rain_chirps_sum_14d_mm", "rain_chirps_sum_3d_mm", "rain_chirps_sum_7d_mm", "rain_mm", "rain_nasa_sum_14d_mm", "rain_nasa_sum_3d_mm", "rain_nasa_sum_7d_mm", "rh_mean_pct", "sand_pct", "share_bare", "share_built", "share_crop", "share_tree", "soc_g_kg", "solar_rad_mj_m2", "t_max_c", "t_mean_c", "t_min_c", "wind_2m_ms", "wp_ptf_pct"]
for target in ['y_plus_1d_pct', 'y_plus_2d_pct', 'y_plus_3d_pct']:
    m = lgb.Booster(model_file=f'models/lgb_{target}_fold0.txt')
    onnx_m = convert_lightgbm(m, initial_types=[('features', FloatTensorType([None, 30]))])
    import onnx; onnx.save(onnx_m, f'onnx/soilnowcast_{target}.onnx')
```

---
## 5. Architecture locale ml/

```
ml/
  features/          feature_list.yaml, feature_stats.json, shap_summary.csv
  training/          config_production.yaml, train_soilnowcast.py
    metrics/         all_metrics.csv, group_errors.csv, oof_predictions.parquet
    figures/         shap_summary.png, fold_stability.png, group_errors.png
  serving/
    models/lgb/      15 fichiers .txt (5 folds x 3 cibles)
    models/cb/       15 fichiers .cbm (backup)
    models/onnx/     3 fichiers .onnx (1 par cible)
    predictor.py     Classe SoilNowcastPredictor
    api.py           FastAPI app
    Dockerfile, requirements.txt
  evaluation/        evaluate.py, drift_detector.py, monitoring_config.yaml
  registry/          model_card.yaml, data_card.yaml, changelog.md, lineage.json
```

---
## 6. Classe d'inference SoilNowcastPredictor

```python
# serving/predictor.py — Autonome, zero dependance OctOpus
import lightgbm as lgb, numpy as np
from pathlib import Path

class SoilNowcastPredictor:
    TARGETS = ['y_plus_1d_pct', 'y_plus_2d_pct', 'y_plus_3d_pct']
    FEATURES = ["bulk_density_g_cm3", "clay_pct", "doy_cos", "doy_sin", "et0_pm_mean_7d_mm", "et0_pm_mm", "fc_ptf_pct", "ph_h2o", "pressure_hpa", "rain_chirps_mm", "rain_chirps_sum_14d_mm", "rain_chirps_sum_3d_mm", "rain_chirps_sum_7d_mm", "rain_mm", "rain_nasa_sum_14d_mm", "rain_nasa_sum_3d_mm", "rain_nasa_sum_7d_mm", "rh_mean_pct", "sand_pct", "share_bare", "share_built", "share_crop", "share_tree", "soc_g_kg", "solar_rad_mj_m2", "t_max_c", "t_mean_c", "t_min_c", "wind_2m_ms", "wp_ptf_pct"]

    def __init__(self, model_dir, n_folds=5):
        self.models = {}
        for t in self.TARGETS:
            self.models[t] = [lgb.Booster(model_file=str(
                Path(model_dir)/f'lgb_{t}_fold{i}.txt')) for i in range(n_folds)]
        self.n_folds = n_folds

    def predict(self, X):
        return {t: np.clip(sum(m.predict(X) for m in ms)/self.n_folds, 0, 100)
                for t, ms in self.models.items()}

    def predict_with_confidence(self, X):
        out = {}
        for t, ms in self.models.items():
            preds = np.array([m.predict(X) for m in ms])
            mu, sigma = preds.mean(0), preds.std(0)
            out[t] = {'mean': np.clip(mu,0,100), 'std': sigma,
                      'lower': np.clip(mu-1.96*sigma,0,100),
                      'upper': np.clip(mu+1.96*sigma,0,100)}
        return out
```

---
## 7. Endpoints FastAPI recommandes

| Endpoint | Methode | Description |
|---|---|---|
| `/predict` | POST | Prediction simple (moyenne 5 folds) |
| `/predict/confidence` | POST | Prediction avec IC 95% |
| `/alert` | POST | Alerte irrigation (secheresse/exces) |
| `/health` | GET | Statut API + version |
| `/model/info` | GET | Features, metriques, periode |
| `/batch` | POST | Prediction CSV (toutes cellules) |

### Seuils d'alerte metier

| Scenario | Condition | Action |
|---|---|---|
| Secheresse | Humidite predite < 15% J+1 | SMS + irrigation recommandee |
| Exces eau | Humidite predite > 80% J+1 | Reporter irrigation |
| Zone fiable | R2 groupe > 0.85 | Pilotage automatique |
| Zone incertaine | R2 groupe < 0.70 | Alerte seule, validation terrain |

---
## 8. Procedure de reentrainement futur

### 8.1 Declencheurs

| Declencheur | Condition | Action |
|---|---|---|
| Derive detectee | PSI > 0.2 | Reentrainer |
| Donnees terrain | >= 1000 releves | V2 avec tensiometre |
| Periode | > 6 mois | Reentrainer |
| Source changee | Nouvelle source pluie | Recalibrer features |

### 8.2 V2 — Donnees terrain SmartAgri

```
V1 (proxy NASA)              V2 (terrain + proxy)
30 features meteo/sol        30 features V1
                             + soil_wetness_measured (tensiometre)
                             + soil_temp_c (thermometre)
                             + irrigation_mm (compteur)
                             + ndvi_10m (Sentinel-2)
Cible : proxy NASA           Cible : mesure terrain
R2 = 0.84                    R2 attendu = 0.92-0.95
```

### 8.3 Script de reentrainement

```python
# training/retrain_soilnowcast.py
# Usage: python retrain_soilnowcast.py --data new.parquet --version v2
import argparse, json, lightgbm as lgb, numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from pathlib import Path; from datetime import datetime

SEED = 42
FEATURES_V1 = ["bulk_density_g_cm3", "clay_pct", "doy_cos", "doy_sin", "et0_pm_mean_7d_mm", "et0_pm_mm", "fc_ptf_pct", "ph_h2o", "pressure_hpa", "rain_chirps_mm", "rain_chirps_sum_14d_mm", "rain_chirps_sum_3d_mm", "rain_chirps_sum_7d_mm", "rain_mm", "rain_nasa_sum_14d_mm", "rain_nasa_sum_3d_mm", "rain_nasa_sum_7d_mm", "rh_mean_pct", "sand_pct", "share_bare", "share_built", "share_crop", "share_tree", "soc_g_kg", "solar_rad_mj_m2", "t_max_c", "t_mean_c", "t_min_c", "wind_2m_ms", "wp_ptf_pct"]
TARGETS = ['y_plus_1d_pct', 'y_plus_2d_pct', 'y_plus_3d_pct']
V2_EXTRAS = ['soil_wetness_measured','soil_temp_c','irrigation_mm','ndvi_10m']
LGB_PARAMS = {"learning_rate": 0.05, "max_depth": 8, "num_leaves": 63, "min_child_samples": 50, "subsample": 0.8, "colsample_bytree": 0.8, "reg_alpha": 0.1, "reg_lambda": 1.0}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--version', default='v2')
    args = ap.parse_args()
    df = pd.read_parquet(args.data)
    feats = list(FEATURES_V1)
    for f in V2_EXTRAS:
        if f in df.columns: feats.append(f)
    X, groups = df[feats].values, df['power_cell_id'].values
    out = Path('models')/args.version; out.mkdir(parents=True, exist_ok=True)
    for target in TARGETS:
        y = df[target].values
        for fold,(tr,va) in enumerate(GroupKFold(5).split(X,y,groups)):
            ds = lgb.Dataset(X[tr],y[tr])
            dv = lgb.Dataset(X[va],y[va],reference=ds)
            m = lgb.train(LGB_PARAMS, ds, 2000, valid_sets=[dv],
                         callbacks=[lgb.early_stopping(50)])
            m.save_model(str(out/f'lgb_{target}_fold{fold}.txt'))
            p = m.predict(X[va])
            print(f'{target} f{fold}: RMSE={np.sqrt(mean_squared_error(y[va],p)):.3f}')

if __name__=='__main__': main()
```

---
## 9. Fiabilite par zone (71 cellules, J+1, LightGBM)

| Categorie | Condition | Cellules | % | Action |
|---|---|---|---|---|
| Excellent | R2 > 0.85 | 29 | 41% | Pilotage automatique |
| Bon | 0.70-0.85 | 13 | 18% | Recommandation + validation |
| Modere | 0.50-0.70 | 8 | 11% | Alerte uniquement |
| Faible | R2 <= 0.50 | 21 | 30% | Capteur requis |

---
## 10. Licences et conformite commerciale

| Source/Composant | Licence | Commercial |
|---|---|---|
| NASA POWER | Open Data Policy | oui (attribution) |
| CHIRPS v3 | CC BY 4.0 | oui |
| iSDAsoil / SoilGrids | CC BY 4.0 | oui |
| ESA WorldCover | CC BY 4.0 | oui |
| LightGBM | MIT | oui |
| XGBoost / CatBoost | Apache 2.0 | oui |
| ONNX Runtime | MIT | oui |
| FastAPI | MIT | oui |

> 100% compatible usage commercial. Zero dependance OctOpus en inference.

---
## 11. Checklist de transfert post-challenge

```
[ ] 1. Telecharger les artefacts depuis OctOpus (section 4)
[ ] 2. Reconstituer ml/ (section 5)
[ ] 3. pip install lightgbm fastapi uvicorn numpy pandas scikit-learn
[ ] 4. Charger les 15 modeles LightGBM
[ ] 5. Tests parite ONNX (section 4)
[ ] 6. uvicorn api:app --host 0.0.0.0 --port 8000
[ ] 7. Tester /predict avec donnees reelles
[ ] 8. Tester /alert scenario secheresse
[ ] 9. Integrer dans pipeline SmartAgri
[ ] 10. Configurer monitoring de derive
```

---
## 12. Resume executif

| Attribut | Valeur |
|---|---|
| **Champion** | LightGBM (RMSE = 7.447) |
| **R2 J+1** | 0.8375 |
| **R2 J+2** | 0.8369 |
| **R2 J+3** | 0.8314 |
| **Features** | 30 retenues (3 tiers SHAP) / 3 rejetees |
| **Modeles** | 45 (3 algos x 3 cibles x 5 folds) |
| **Export** | LGB .txt + CB .cbm + ONNX + JSON config |
| **Zones fiables** (R2>0.70) | 42/71 (59%) |
| **Cout** | < 2 $ sur 59.70 $ |
| **Licence** | 100% open + commercial |
| **Endpoints** | /predict, /predict/confidence, /alert, /health, /model/info, /batch |
| **V2** | +5-10 pts R2 avec donnees terrain |

---
*Document genere a partir des artefacts SoilNowcast (45 modeles, 258 440 lignes).*
*Equipe Agri-Moderne 5.0 — PAS Challenge 2026.*