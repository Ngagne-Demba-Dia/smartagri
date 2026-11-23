from pathlib import Path
import numpy as np
import pandas as pd
SEED = 42
rng = np.random.default_rng(SEED)
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)
INPUTS = {key: str(Path("inputs") / key) for key in ['pf_8cffb44cb1be493c9a5fd829']}
def progress(message="", **fields):
    import json as _j, sys as _s, time as _t
    try:
        _r = dict(fields, message=str(message)[:200], t=round(_t.time(), 2))
        _l = _j.dumps(_r, default=str)
        print("[progress] " + _l, flush=True)
        with open(OUTPUT / ".progress.jsonl", "a") as _f:
            _f.write(_l + "\n")
    except Exception:
        pass
def _rt_setup():
    import json as _j, sys as _s
    here = globals().get("__file__")
    try:
        pd.set_option("future.infer_string", False)
        _select = pd.DataFrame.select_dtypes

        def select_dtypes(self, include=None, exclude=None):
            def classic(value):
                if value is None:
                    return None
                items = list(value) if isinstance(value, (list, tuple, set, frozenset)) else [value]
                out = []
                for item in items:
                    if item is str or (isinstance(item, str) and item in ("str", "string")):
                        out.append(object)
                        if item == "string":
                            out.append(item)
                    else:
                        out.append(item)
                return [x for i, x in enumerate(out) if not any(x is y for y in out[:i])]
            return _select(self, include=classic(include), exclude=classic(exclude))
        pd.DataFrame.select_dtypes = select_dtypes
    except Exception:
        pass
    _base = _j.JSONEncoder.default

    def default(self, value):
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, (pd.Series, pd.Index)):
            return value.tolist()
        if isinstance(value, pd.DataFrame):
            return value.to_dict(orient="records")
        if isinstance(value, (pd.Timestamp, pd.Timedelta, Path)):
            return str(value)
        if isinstance(value, (set, frozenset)):
            return sorted(value, key=str)
        if value is pd.NA or value is pd.NaT:
            return None
        return _base(self, value)
    _j.JSONEncoder.default = default

    def diagnose(kind, error, tb):
        import re as _r, difflib as _d
        lines, message, frames, seen = [], str(error), [], set()

        def collect(space):
            for key, value in list(space.items()):
                if isinstance(value, pd.DataFrame) and id(value) not in seen and not str(key).startswith("_"):
                    seen.add(id(value))
                    frames.append((str(key), value))
        step = tb
        while step is not None:
            if step.tb_frame.f_code.co_filename == here:
                collect(step.tb_frame.f_locals)
            step = step.tb_next
        collect(globals())
        frames = frames[:8]

        def text_columns(frame):
            return [c for c in frame.columns if not (pd.api.types.is_numeric_dtype(frame[c])
                    or pd.api.types.is_bool_dtype(frame[c]) or pd.api.types.is_datetime64_any_dtype(frame[c]))]
        if "could not convert string to" in message:
            told = {}
            for label, frame in frames:
                columns = tuple(str(c) for c in text_columns(frame))
                if columns:
                    told.setdefault(columns, []).append((label, frame))
            value = _r.search(r"could not convert string to \w+: '?([^']*)'?", message)
            value = value.group(1) if value else None
            for columns, where in list(told.items())[:2]:
                frame = where[0][1]
                holds = [c for c in columns if value and c in frame.columns
                         and bool((frame[c].astype(str) == value).any())]
                if holds:
                    lines.append(f"{value!r} is a value of column {', '.join(holds[:3])}.")
                shown = "; ".join(
                    f"{c} (values: {', '.join(str(v)[:24] for v in frame[c].dropna().unique()[:4])})"
                    for c in columns[:8])
                lines.append(
                    f"Text columns in {', '.join(label for label, _ in where[:4])}: {shown}. They reached a model "
                    "that needs numbers. Encode exactly these columns by name inside the model pipeline "
                    "(ColumnTransformer with OneHotEncoder(handle_unknown='ignore'), fitted on the training rows "
                    "only), or leave them out of the features. A table read back from CSV holds the text again: "
                    "an encoding done in an earlier call is not in the file unless the encoded columns were saved.")
        if kind.__name__ == "KeyError" and error.args and isinstance(error.args[0], str):
            key = error.args[0]
            for label, frame in frames[:3]:
                names = [str(c) for c in frame.columns]
                if key not in names:
                    close = _d.get_close_matches(key, names, n=4, cutoff=0.5)
                    lines.append(f"{label} has no column {key!r}."
                                 + (f" Nearest names: {', '.join(close)}." if close else "")
                                 + f" Its columns: {', '.join(names[:60])}.")
            try:
                if key not in INPUTS and not lines:
                    lines.append("INPUTS holds: " + ", ".join(sorted(str(k) for k in INPUTS)[:30]) + ".")
            except Exception:
                pass
        if "NaN" in message or "missing values" in message or "infinity" in message:
            for label, frame in frames[:4]:
                empty = frame.isna().sum()
                empty = empty[empty > 0].sort_values(ascending=False)
                if len(empty):
                    lines.append(f"Missing values in {label}: "
                                 + ", ".join(f"{c} {int(n)}" for c, n in empty.head(10).items()) + ".")
        if kind.__name__ == "NameError":
            lines.append("Every call is a new program: variables, fitted models and imports of an earlier call do "
                         "not exist here. Define the name in this program, or read what an earlier call saved "
                         "from INPUTS by its file name.")
        if "inconsistent numbers of samples" in message or "shape" in message.lower() or "feature names" in message.lower():
            if frames:
                lines.append("Shapes: " + ", ".join(f"{label} {tuple(frame.shape)}" for label, frame in frames) + ".")
        try:
            from importlib import metadata as _m
            found = []
            for library in ("pandas", "numpy", "scikit-learn", "xgboost", "lightgbm", "catboost", "optuna",
                            "scipy", "matplotlib"):
                try:
                    found.append(library + " " + _m.version(library))
                except Exception:
                    pass
            if found:
                lines.append("Installed versions: " + ", ".join(found) + ".")
        except Exception:
            pass
        return lines

    def stopped(kind, error, tb):
        import traceback as _t
        _t.print_exception(kind, error, tb)
        try:
            for line in diagnose(kind, error, tb):
                print("[diagnosis] " + str(line)[:900], file=_s.stderr)
        except Exception:
            pass
        _s.stderr.flush()
    _s.excepthook = stopped


_rt_setup()

import pandas as pd, numpy as np, zipfile, io, json, time
from sklearn.model_selection import GroupKFold
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score
import lightgbm as lgb
import xgboost as xgb
import catboost as cb

ZIP = INPUTS['octopus_import_bundle.zip']
def read_pq(name):
    with zipfile.ZipFile(ZIP) as zf:
        return pd.read_parquet(io.BytesIO(zf.read(name)))

progress("Chargement données ET0 + NASA POWER", done=0, total=6)
et0 = read_pq('octopus_import/datasets/et0/fao56_et0_national_daily.parquet')
nasa = read_pq('octopus_import/datasets/meteo/nasa_power_national_daily.parquet')

# Merge ET0 target with NASA features
df = nasa.merge(et0[['power_cell_id','date','et0_pm_mm','ra_mj_m2','et0_hargreaves_mm']],
                on=['power_cell_id','date'], how='inner')
df = df.dropna(subset=['et0_pm_mm'])
print(f"Merged: {df.shape}")

# Feature engineering
df['date'] = pd.to_datetime(df['date'])
df['doy'] = df['date'].dt.dayofyear
df['month'] = df['date'].dt.month
df['doy_sin'] = np.sin(2 * np.pi * df['doy'] / 365)
df['doy_cos'] = np.cos(2 * np.pi * df['doy'] / 365)
df['t_range_c'] = df['t_max_c'] - df['t_min_c']

TARGET = 'et0_pm_mm'
FEATURES = ['t_min_c','t_max_c','t_mean_c','rh_mean_pct','wind_2m_ms',
            'solar_rad_mj_m2','pressure_hpa','rain_mm','ra_mj_m2',
            'et0_hargreaves_mm','doy_sin','doy_cos','month','t_range_c','lat','lon']
GROUP = 'power_cell_id'

X = df[FEATURES].values
y = df[TARGET].values
groups = df[GROUP].values

gkf = GroupKFold(n_splits=5)
all_metrics = []

MODELS = {
    'LightGBM': lambda: lgb.LGBMRegressor(
        n_estimators=1000, learning_rate=0.05, max_depth=8,
        num_leaves=63, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0, min_child_samples=50,
        verbosity=-1, n_jobs=2,
        callbacks=[lgb.early_stopping(50, verbose=False)]
    ),
    'XGBoost': lambda: xgb.XGBRegressor(
        n_estimators=1000, learning_rate=0.05, max_depth=8,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0, min_child_weight=50,
        tree_method='hist', n_jobs=2,
        early_stopping_rounds=50, eval_metric='rmse'
    ),
    'CatBoost': lambda: cb.CatBoostRegressor(
        iterations=1000, learning_rate=0.05, depth=8,
        subsample=0.8, l2_leaf_reg=3.0,
        verbose=0, early_stopping_rounds=50
    ),
}

importances = {m: np.zeros(len(FEATURES)) for m in MODELS}
group_errors = []

for mi, (mname, mfactory) in enumerate(MODELS.items()):
    progress(f"Entraînement {mname}", done=mi+1, total=6)
    for fold, (tr_idx, va_idx) in enumerate(gkf.split(X, y, groups)):
        X_tr, X_va = X[tr_idx], X[va_idx]
        y_tr, y_va = y[tr_idx], y[va_idx]
        
        model = mfactory()
        if mname == 'XGBoost':
            model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
            best_iter = model.best_iteration
        elif mname == 'LightGBM':
            model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)])
            best_iter = model.best_iteration_
        else:
            model.fit(X_tr, y_tr, eval_set=(X_va, y_va))
            best_iter = model.best_iteration_
        
        preds = model.predict(X_va)
        rmse = root_mean_squared_error(y_va, preds)
        mae = mean_absolute_error(y_va, preds)
        r2 = r2_score(y_va, preds)
        
        all_metrics.append({
            'model': mname, 'target': TARGET, 'fold': fold,
            'rmse': round(rmse, 4), 'mae': round(mae, 4),
            'r2': round(r2, 4), 'best_iter': best_iter
        })
        
        # Feature importance
        if mname == 'LightGBM':
            importances[mname] += model.feature_importances_ / 5
        elif mname == 'XGBoost':
            importances[mname] += model.feature_importances_ / 5
        else:
            importances[mname] += model.feature_importances_ / 5
        
        # Group errors (last fold only)
        if fold == 4:
            va_groups = groups[va_idx]
            for g in np.unique(va_groups):
                mask = va_groups == g
                ge_rmse = root_mean_squared_error(y_va[mask], preds[mask])
                ge_r2 = r2_score(y_va[mask], preds[mask]) if len(y_va[mask]) > 1 else np.nan
                group_errors.append({
                    'group': g, 'model': mname, 'target': TARGET,
                    'rmse': round(ge_rmse, 4), 'mae': round(mean_absolute_error(y_va[mask], preds[mask]), 4),
                    'r2': round(ge_r2, 4), 'n': int(mask.sum()),
                    'mean_true': round(float(y_va[mask].mean()), 4)
                })
        
        print(f"  {mname} fold {fold}: RMSE={rmse:.4f} MAE={mae:.4f} R²={r2:.4f}")

progress("Sauvegarde résultats ET0", done=5, total=6)

# Save metrics
met_df = pd.DataFrame(all_metrics)
met_df.to_csv(OUTPUT / 'et0_forecast_all_metrics.csv', index=False)

# Feature importance
fi_df = pd.DataFrame({
    'feature': FEATURES,
    'lgb_importance': importances['LightGBM'],
    'xgb_importance': importances['XGBoost'],
    'cb_importance': importances['CatBoost'],
})
fi_df.to_csv(OUTPUT / 'et0_forecast_feature_importance.csv', index=False)

# Group errors
ge_df = pd.DataFrame(group_errors)
ge_df.to_csv(OUTPUT / 'et0_forecast_group_errors.csv', index=False)

# Summary
print("\n=== RÉSUMÉ A2 ET0 FORECAST ===")
for m in ['LightGBM','XGBoost','CatBoost']:
    sub = met_df[met_df['model']==m]
    print(f"{m}: RMSE={sub['rmse'].mean():.4f} MAE={sub['mae'].mean():.4f} R²={sub['r2'].mean():.4f}")

best_model = met_df.groupby('model')['rmse'].mean().idxmin()
print(f"\nChampion: {best_model}")

progress("ET0 Forecast terminé", done=6, total=6)
result = f"ET0 Forecast done. Champion: {best_model}"

