# 86 — SmartAgri Feature Store
## Architecture Complète du Feature Store SmartAgri92

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Production-ready design

---

## 1. Architecture

### 1.1 Vue d'ensemble

```
┌───────────────────────────────────────────────────────────┐
│                  SmartAgri Feature Store                    │
├────────────────────────┬──────────────────────────────────┤
│    Offline Store       │       Online Store               │
│                        │                                  │
│  ┌────────────────┐    │   ┌──────────────────────┐       │
│  │ DuckDB/Parquet │    │   │ Redis 7 (< 1ms)      │       │
│  │ Historique     │    │   │ Dernières valeurs     │       │
│  │ Training batch │    │   │ TTL par feature group │       │
│  └────────────────┘    │   └──────────────────────┘       │
│                        │                                  │
│  Backfill, validation  │   Serving temps réel             │
│  Audit, reproductibilité│   Inférence < 200ms            │
├────────────────────────┴──────────────────────────────────┤
│                  Feature Registry (catalogue)              │
│  • 130+ features cataloguées                               │
│  • Métadonnées, types, propriétaire, version               │
│  • Lineage source → transformation → feature → modèle     │
│  • Monitoring freshness & distribution drift               │
└───────────────────────────────────────────────────────────┘
```

### 1.2 Entités

| Entité | Granularité | Cardinalité | Description |
|--------|-------------|-------------|-------------|
| `cell_id` | 0,05° (~5,5 km) | 6 945 | Grille fine nationale |
| `power_cell_id` | 0,5°×0,625° | 76 | Grille météo NASA POWER |
| `market_id` | Point | 79 | Marchés WFP |
| `crop` | National | ~15 | Cultures FAOSTAT |

---

## 2. Catalogue complet des features

### 2.1 Feature Group: `meteo_daily`

| Feature | Type | Source | Unité | Range | TTL |
|---------|------|--------|-------|-------|-----|
| t_min_c | float64 | NASA POWER | °C | [-5, 50] | 48h |
| t_max_c | float64 | NASA POWER | °C | [0, 55] | 48h |
| t_mean_c | float64 | NASA POWER | °C | [-2, 52] | 48h |
| rh_mean_pct | float64 | NASA POWER | % | [0, 100] | 48h |
| wind_2m_ms | float64 | NASA POWER | m/s | [0, 15] | 48h |
| solar_rad_mj_m2 | float64 | NASA POWER | MJ/m² | [0, 35] | 48h |
| pressure_hpa | float64 | NASA POWER | hPa | [980, 1030] | 48h |

**Entité** : `power_cell_id` — **Granularité** : quotidienne — **329 232 lignes**

### 2.2 Feature Group: `rain_daily`

| Feature | Type | Source | Unité | Range | TTL |
|---------|------|--------|-------|-------|-----|
| rain_mm | float64 | NASA POWER | mm | [0, 200] | 48h |
| rain_chirps_mm | float64 | CHIRPS v3 | mm | [0, 300] | 120h |
| is_provisional | bool | CHIRPS v3 | — | {0,1} | 120h |

**Entité** : `cell_id` (rain_chirps) / `power_cell_id` (rain_mm) — **25M+ lignes CHIRPS**

### 2.3 Feature Group: `rain_rolling`

| Feature | Type | Computation | Fenêtre | TTL |
|---------|------|------------|---------|-----|
| rain_nasa_sum_3d_mm | float64 | SUM(rain_mm, 3d) | 3 jours | 48h |
| rain_nasa_sum_7d_mm | float64 | SUM(rain_mm, 7d) | 7 jours | 48h |
| rain_nasa_sum_14d_mm | float64 | SUM(rain_mm, 14d) | 14 jours | 48h |
| rain_chirps_sum_3d_mm | float64 | SUM(rain_chirps_mm, 3d) | 3 jours | 120h |
| rain_chirps_sum_7d_mm | float64 | SUM(rain_chirps_mm, 7d) | 7 jours | 120h |
| rain_chirps_sum_14d_mm | float64 | SUM(rain_chirps_mm, 14d) | 14 jours | 120h |

**Entité** : héritée de la source — **Critique pour A1 (top 3 features) et A4**

### 2.4 Feature Group: `et0_daily`

| Feature | Type | Source | Computation | TTL |
|---------|------|--------|------------|-----|
| et0_pm_mm | float64 | FAO-56 | Penman-Monteith | 48h |
| et0_pm_mean_7d_mm | float64 | Dérivée | MEAN(et0_pm_mm, 7d) | 48h |

**Entité** : `power_cell_id` — **329 232 lignes**

### 2.5 Feature Group: `soil_static`

| Feature | Type | Source | Unité | Profondeur |
|---------|------|--------|-------|-----------|
| sand_pct | float64 | iSDAsoil | % | 0-20 cm |
| clay_pct | float64 | iSDAsoil | % | 0-20 cm |
| soc_g_kg | float64 | iSDAsoil | g/kg | 0-20 cm |
| ph_h2o | float64 | iSDAsoil | — | 0-20 cm |
| bulk_density_g_cm3 | float64 | iSDAsoil | g/cm³ | 0-20 cm |
| fc_ptf_pct | float64 | PTF dérivée | % | — |
| wp_ptf_pct | float64 | PTF dérivée | % | — |

**Entité** : `cell_id` — **TTL** : illimité (statique) — **13 890 lignes (2 profondeurs)**

### 2.6 Feature Group: `landcover`

| Feature | Type | Source | Unité |
|---------|------|--------|-------|
| share_crop | float64 | ESA WorldCover | fraction [0,1] |
| share_tree | float64 | ESA WorldCover | fraction [0,1] |
| share_bare | float64 | ESA WorldCover | fraction [0,1] |
| share_built | float64 | ESA WorldCover | fraction [0,1] |

**Entité** : `cell_id` — **TTL** : annuel — **6 945 lignes**

### 2.7 Feature Group: `temporal`

| Feature | Type | Computation |
|---------|------|------------|
| doy_sin | float64 | sin(2π × day_of_year / 365) |
| doy_cos | float64 | cos(2π × day_of_year / 365) |

**Entité** : date — **TTL** : temps réel (calculé)

### 2.8 Feature Group: `soil_wetness` (cible SoilNowcast)

| Feature | Type | Source | Rôle |
|---------|------|--------|------|
| soil_wetness_root_pct | float64 | NASA GEOS | Cible A1 |
| y_plus_1d_pct | float64 | Décalée | Cible A1 J+1 |
| y_plus_2d_pct | float64 | Décalée | Cible A1 J+2 |
| y_plus_3d_pct | float64 | Décalée | Cible A1 J+3 |

### 2.9 Feature Group: `ndvi_monthly`

| Feature | Type | Source |
|---------|------|--------|
| ndvi_mean | float64 | Sentinel-2 L2A |
| ndvi_std | float64 | Sentinel-2 L2A |
| cloud_pct | float64 | SCL mask |
| valid_pixels | int | SCL mask |

**Entité** : `cell_id` — **Granularité** : mensuelle — **26 198 lignes**

### 2.10 Feature Group: `market_prices`

| Feature | Type | Source | Unité |
|---------|------|--------|-------|
| price_fcfa_kg | float64 | WFP | FCFA/kg |
| commodity | string | WFP | — |
| market | string | WFP | — |
| price_lag_1m | float64 | Dérivée | FCFA/kg |
| price_rolling_3m | float64 | Dérivée | FCFA/kg |

**Entité** : `market_id` × `commodity` — **55 283 lignes**

### 2.11 Feature Group: `crop_kc`

| Feature | Type | Source |
|---------|------|--------|
| kc | float64 | FAO-56 | Coefficient cultural |
| crop_phase | string | FAO-56 | Phase phénologique |

**Entité** : `crop` × `doy` — **900 lignes** — 17 cultures

---

## 3. Matrice Features × Modèles

| Feature Group | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 |
|---------------|----|----|----|----|----|----|----|----|-----|
| meteo_daily | ✅ | ✅ | ✅ | ✅ | ○ | ○ | ○ | ✅ | ○ |
| rain_daily | ✅ | ○ | ✅ | ✅ | ○ | ✅ | ○ | ✅ | ○ |
| rain_rolling | ✅ | ○ | ○ | ✅ | ○ | ○ | ○ | ✅ | ○ |
| et0_daily | ✅ | — | ○ | ○ | ○ | ✅ | ○ | ✅ | ○ |
| soil_static | ✅ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| landcover | ✅ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| temporal | ✅ | ✅ | ○ | ✅ | ✅ | ✅ | ✅ | ✅ | ○ |
| ndvi_monthly | ○ | ○ | ○ | ○ | ○ | ○ | ✅ | ○ | ○ |
| market_prices | ○ | ○ | ○ | ○ | ✅ | ○ | ○ | ○ | ✅ |
| crop_kc | ○ | ○ | ○ | ○ | ○ | ✅ | ○ | ○ | ○ |

✅ = feature directe | ○ = non utilisée | — = cible du modèle

---

## 4. Lineage

### 4.1 Graphe de lineage

```
NASA POWER ──→ meteo_daily ──→ rain_rolling ──┐
                    │                          │
                    ├──→ et0_daily              │
                    │                          │
CHIRPS v3 ───→ rain_daily ───→ rain_rolling ──┤
                                               │
iSDAsoil ────→ soil_static ───────────────────┤
                                               ├──→ A1 SoilNowcast
ESA WC ──────→ landcover ─────────────────────┤
                                               │
Calendar ────→ temporal ──────────────────────┘

NASA POWER ──→ meteo_daily ──→ A2 ET0 Forecast
CHIRPS v3 ───→ rain_daily ──→ rain_rolling ──→ A4 Rain Intelligence
Sentinel-2 ──→ ndvi_monthly ─────────────────→ A7 NDVI Anomaly
WFP ─────────→ market_prices ────────────────→ A5 Price Forecast
FAOSTAT ─────→ yield_history ────────────────→ A3 Yield Forecast
FAO-56 ──────→ crop_kc ─────────────────────→ A6 Crop Calendar
```

### 4.2 Traçabilité

Chaque feature porte :
```python
@dataclass
class FeatureLineage:
    feature_name: str
    feature_group: str
    source_dataset: str           # "nasa_power_national_daily"
    source_version: str           # "v2026.11.18"
    transformation: str           # "rolling_sum_14d" | "identity" | "ptf_derivation"
    transformation_code_hash: str # SHA-256 du code de transformation
    created_at: datetime
    validated_at: Optional[datetime]
```

---

## 5. Validation de schéma

### 5.1 Contrats par Feature Group

```python
FEATURE_CONTRACTS = {
    "meteo_daily": {
        "entity_key": "power_cell_id",
        "timestamp_key": "date",
        "features": {
            "t_min_c": {"type": "float64", "min": -10, "max": 55, "nullable": False},
            "t_max_c": {"type": "float64", "min": -5, "max": 60, "nullable": False},
            "rh_mean_pct": {"type": "float64", "min": 0, "max": 100, "nullable": False},
            "wind_2m_ms": {"type": "float64", "min": 0, "max": 20, "nullable": False},
            "solar_rad_mj_m2": {"type": "float64", "min": 0, "max": 40, "nullable": False},
            "pressure_hpa": {"type": "float64", "min": 950, "max": 1050, "nullable": False},
        },
        "cross_validations": [
            ("t_max_c", ">=", "t_min_c"),
        ]
    }
}
```

### 5.2 Validation automatique

```python
class FeatureValidator:
    def validate_schema(self, data: pd.DataFrame, contract: dict) -> ValidationResult:
        """Vérifie types, ranges, nulls, cross-validations."""

    def validate_freshness(self, feature_group: str) -> FreshnessResult:
        """Vérifie que les données sont à jour vs SLA."""

    def validate_distribution(self, data: pd.DataFrame,
                              reference: pd.DataFrame) -> DriftResult:
        """Détecte le drift vs distribution de référence."""
```

---

## 6. Freshness Monitoring

### 6.1 SLAs par source

| Source | Fréquence | SLA | Alerte | Critique |
|--------|-----------|-----|--------|----------|
| NASA POWER | Quotidienne | J+2 | J+3 | J+5 |
| CHIRPS v3 | Quotidienne | J+5 | J+7 | J+10 |
| FAO-56 ET0 | Calculée | Avec NASA | — | — |
| iSDAsoil | Statique | Annuelle | 18 mois | 24 mois |
| ESA WorldCover | Annuelle | Annuelle | 18 mois | 24 mois |
| Sentinel-2 NDVI | Mensuelle | M+1 | M+2 | M+3 |
| WFP Prices | Mensuelle | M+1 | M+2 | M+4 |
| FAOSTAT | Annuelle | An+1 | An+2 | An+3 |

### 6.2 Impact sur les modèles

| Retard | Impact A1 | Impact A4 | Impact A8 |
|--------|-----------|-----------|-----------|
| NASA J+3 | Confiance -10% | Confiance -10% | Confiance -10% |
| NASA J+5 | Abstention | Abstention | Abstention |
| CHIRPS J+7 | Confiance -15% | Confiance -15% | Confiance -15% |
| CHIRPS J+10 | Fallback NASA seul | Fallback NASA | Fallback NASA |

---

## 7. API de serving

### 7.1 Offline API (batch)

```python
@app.post("/features/batch")
def get_features_batch(
    entity_ids: List[str],
    feature_groups: List[str],
    date_range: Tuple[date, date]
) -> pd.DataFrame:
    """Retourne les features pour un batch d'entités et une plage de dates."""
```

### 7.2 Online API (temps réel)

```python
@app.get("/features/online/{entity_id}")
def get_features_online(
    entity_id: str,
    feature_groups: List[str]
) -> dict:
    """
    Retourne les dernières valeurs depuis Redis.
    Latence cible: < 5ms.
    Fallback: lecture Parquet si Redis miss.
    """
```

---

## 8. Backfill Strategy

### 8.1 Scénarios de backfill

| Scénario | Action | Durée | Risque |
|----------|--------|-------|--------|
| Nouvelle feature ajoutée | Calculer sur tout l'historique | 2-8h | Faible |
| Source mise à jour (corrections) | Recalculer features affectées | 1-4h | Moyen |
| Nouveau modèle nécessite plus d'historique | Étendre la fenêtre | 4-12h | Faible |
| Bug détecté dans transformation | Recalculer + réentraîner modèles | 8-24h | Élevé |

### 8.2 Procédure

```
1. Créer un snapshot de l'état actuel
2. Exécuter le backfill sur une copie
3. Valider le schéma et les distributions
4. Comparer les métriques modèle avant/après
5. Si OK : promouvoir les nouvelles features
6. Si KO : rollback au snapshot
```

---

## 9. Résumé

| Composant | Statut | Détail |
|-----------|--------|--------|
| Feature Groups | 11 groupes | 130+ features cataloguées |
| Entités | 4 types | cell_id, power_cell_id, market_id, crop |
| Sources | 10 | Toutes open data, licences vérifiées |
| Offline Store | DuckDB/Parquet | Batch training, backfill |
| Online Store | Redis | Inférence < 5ms |
| Validation | Contrats stricts | Types, ranges, cross-validation |
| Freshness | SLAs définis | 8 sources, alertes à 2 niveaux |
| Lineage | Complet | Source → transformation → feature → modèle |
| Backfill | 4 scénarios | Procédure avec rollback |

**Indépendant d'OctOpus. Déployable sur n'importe quelle infrastructure.**
