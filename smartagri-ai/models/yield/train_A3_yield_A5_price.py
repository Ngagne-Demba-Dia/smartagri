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

import pandas as pd, numpy as np, zipfile, io
from sklearn.model_selection import GroupKFold, KFold
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb
import xgboost as xgb
import catboost as cb

ZIP = INPUTS['octopus_import_bundle.zip']
def read_pq(name):
    with zipfile.ZipFile(ZIP) as zf:
        return pd.read_parquet(io.BytesIO(zf.read(name)))

def make_models():
    return {
        'LightGBM': lgb.LGBMRegressor(n_estimators=500,learning_rate=0.05,max_depth=6,
            num_leaves=31,subsample=0.8,colsample_bytree=0.8,min_child_samples=5,
            verbosity=-1,n_jobs=2,callbacks=[lgb.early_stopping(30,verbose=False)]),
        'XGBoost': xgb.XGBRegressor(n_estimators=500,learning_rate=0.05,max_depth=6,
            subsample=0.8,colsample_bytree=0.8,min_child_weight=5,tree_method='hist',
            n_jobs=2,early_stopping_rounds=30,eval_metric='rmse'),
        'CatBoost': cb.CatBoostRegressor(iterations=500,learning_rate=0.05,depth=6,
            subsample=0.8,l2_leaf_reg=3.0,verbose=0,early_stopping_rounds=30),
    }

def train_fold(mname, m, Xtr, ytr, Xva, yva):
    if mname=='XGBoost':
        m.fit(Xtr,ytr,eval_set=[(Xva,yva)],verbose=False)
        return m.best_iteration
    elif mname=='LightGBM':
        m.fit(Xtr,ytr,eval_set=[(Xva,yva)])
        return m.best_iteration_
    else:
        m.fit(Xtr,ytr,eval_set=(Xva,yva))
        return m.best_iteration_

# ===== A3 YIELD =====
progress("A3 Yield — chargement",done=0,total=8)
fao = read_pq('octopus_import/datasets/yields/faostat_senegal_crops_1961_2024.parquet')
df_y = fao.dropna(subset=['yield_t_ha']).copy()
df_y = df_y[df_y['yield_t_ha']>0].copy()
df_y['crop_enc'] = LabelEncoder().fit_transform(df_y['crop'])
df_y['year_norm'] = (df_y['year']-df_y['year'].min())/max(1,df_y['year'].max()-df_y['year'].min())
df_y['decade'] = (df_y['year']//10)*10
if 'area_ha' in df_y.columns:
    df_y['area_ha'] = pd.to_numeric(df_y['area_ha'],errors='coerce').fillna(0)
FEAT_Y = ['year','crop_enc','year_norm','decade','area_ha']
FEAT_Y = [f for f in FEAT_Y if f in df_y.columns]
X_y = df_y[FEAT_Y].values.astype(float); y_y = df_y['yield_t_ha'].values
print(f"Yield: {len(df_y)} rows, {len(FEAT_Y)} features")

kf = KFold(n_splits=5,shuffle=True,random_state=42)
ym = []; yi = {}
for mi,mn in enumerate(['LightGBM','XGBoost','CatBoost']):
    progress(f"A3 {mn}",done=mi+1,total=8)
    imp = np.zeros(len(FEAT_Y))
    for fold,(tr,va) in enumerate(kf.split(X_y)):
        m = make_models()[mn]
        bi = train_fold(mn,m,X_y[tr],y_y[tr],X_y[va],y_y[va])
        p = m.predict(X_y[va])
        ym.append({'model':mn,'target':'yield_t_ha','fold':fold,
            'rmse':round(root_mean_squared_error(y_y[va],p),4),
            'mae':round(mean_absolute_error(y_y[va],p),4),
            'r2':round(r2_score(y_y[va],p),4),'best_iter':bi})
        imp += m.feature_importances_/5
    yi[mn]=imp
    sub=[x for x in ym if x['model']==mn]
    print(f"  {mn}: RMSE={np.mean([x['rmse'] for x in sub]):.4f} R²={np.mean([x['r2'] for x in sub]):.4f}")
pd.DataFrame(ym).to_csv(OUTPUT/'yield_forecast_all_metrics.csv',index=False)
pd.DataFrame({'feature':FEAT_Y,'lgb':yi['LightGBM'],'xgb':yi['XGBoost'],'cb':yi['CatBoost']}).to_csv(OUTPUT/'yield_forecast_feature_importance.csv',index=False)

# ===== A5 PRICE =====
progress("A5 Price — chargement",done=4,total=8)
prices = read_pq('octopus_import/datasets/market_prices/wfp_senegal_food_prices.parquet')
print(f"Prices cols: {list(prices.columns)}")
print(f"Dtypes:\n{prices.dtypes}")

# Use price_fcfa_kg as numeric target
price_col = 'price_fcfa_kg'
df_p = prices.copy()
df_p[price_col] = pd.to_numeric(df_p[price_col], errors='coerce')
df_p = df_p.dropna(subset=[price_col])
df_p = df_p[df_p[price_col]>0].copy()
df_p['date'] = pd.to_datetime(df_p['date'])
df_p['year'] = df_p['date'].dt.year
df_p['month'] = df_p['date'].dt.month
df_p['doy_sin'] = np.sin(2*np.pi*df_p['date'].dt.dayofyear/365)
df_p['doy_cos'] = np.cos(2*np.pi*df_p['date'].dt.dayofyear/365)

for col in ['crop','market','region','category']:
    if col in df_p.columns:
        df_p[col+'_enc'] = LabelEncoder().fit_transform(df_p[col].astype(str))

FEAT_P = ['year','month','doy_sin','doy_cos']
for c in ['crop_enc','market_enc','region_enc','category_enc','lat','lon']:
    if c in df_p.columns and df_p[c].notna().sum()>len(df_p)*0.3:
        FEAT_P.append(c)

df_p = df_p.dropna(subset=FEAT_P+[price_col])
for c in FEAT_P:
    df_p[c] = pd.to_numeric(df_p[c], errors='coerce')
df_p = df_p.dropna(subset=FEAT_P)

X_p = df_p[FEAT_P].values.astype(float)
y_p = df_p[price_col].values.astype(float)
groups_p = df_p['market_enc'].values if 'market_enc' in df_p.columns else np.zeros(len(df_p))
ng = len(np.unique(groups_p)); k = min(5, ng)
print(f"Price: {len(df_p)} rows, {ng} markets, {len(FEAT_P)} features: {FEAT_P}")

gkf = GroupKFold(n_splits=k)
pm_list = []; pi = {}; pge = []
for mi,mn in enumerate(['LightGBM','XGBoost','CatBoost']):
    progress(f"A5 {mn}",done=mi+5,total=8)
    imp = np.zeros(len(FEAT_P))
    for fold,(tr,va) in enumerate(gkf.split(X_p,y_p,groups_p)):
        m = make_models()[mn]
        bi = train_fold(mn,m,X_p[tr],y_p[tr],X_p[va],y_p[va])
        pred = m.predict(X_p[va])
        pm_list.append({'model':mn,'target':price_col,'fold':fold,
            'rmse':round(root_mean_squared_error(y_p[va],pred),2),
            'mae':round(mean_absolute_error(y_p[va],pred),2),
            'r2':round(r2_score(y_p[va],pred),4),'best_iter':bi})
        imp += m.feature_importances_/k
        if fold==k-1:
            vg = groups_p[va]
            for g in np.unique(vg):
                mask=vg==g
                if mask.sum()>=2:
                    pge.append({'group':int(g),'model':mn,'target':price_col,
                        'rmse':round(root_mean_squared_error(y_p[va][mask],pred[mask]),2),
                        'r2':round(r2_score(y_p[va][mask],pred[mask]),4),'n':int(mask.sum())})
    pi[mn]=imp
    sub=[x for x in pm_list if x['model']==mn]
    print(f"  {mn}: RMSE={np.mean([x['rmse'] for x in sub]):.2f} R²={np.mean([x['r2'] for x in sub]):.4f}")

pd.DataFrame(pm_list).to_csv(OUTPUT/'price_forecast_all_metrics.csv',index=False)
pd.DataFrame({'feature':FEAT_P,'lgb':pi['LightGBM'],'xgb':pi['XGBoost'],'cb':pi['CatBoost']}).to_csv(OUTPUT/'price_forecast_feature_importance.csv',index=False)
pd.DataFrame(pge).to_csv(OUTPUT/'price_forecast_group_errors.csv',index=False)

progress("A3+A5 terminés",done=8,total=8)
ym_df=pd.DataFrame(ym); pm_df=pd.DataFrame(pm_list)
print(f"\nA3 Champion: {ym_df.groupby('model')['rmse'].mean().idxmin()} R²={ym_df.groupby('model')['r2'].mean().max():.4f}")
print(f"A5 Champion: {pm_df.groupby('model')['rmse'].mean().idxmin()} R²={pm_df.groupby('model')['r2'].mean().max():.4f}")
result="A3+A5 done"

