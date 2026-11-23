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
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.metrics import f1_score, accuracy_score, silhouette_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.cluster import KMeans
import lightgbm as lgb, xgboost as xgb, catboost as cb

ZIP = INPUTS['octopus_import_bundle.zip']
def read_pq(name):
    with zipfile.ZipFile(ZIP) as zf:
        return pd.read_parquet(io.BytesIO(zf.read(name)))

def train_es(mn,m,Xtr,ytr,Xva,yva):
    if mn=='XGBoost':
        m.fit(Xtr,ytr,eval_set=[(Xva,yva)],verbose=False); return m.best_iteration
    elif mn=='LightGBM':
        m.fit(Xtr,ytr,eval_set=[(Xva,yva)]); return m.best_iteration_
    else:
        m.fit(Xtr,ytr,eval_set=(Xva,yva)); return m.best_iteration_

all_metrics = []

# ===== A6 CROP CALENDAR =====
progress("A6",done=0,total=9)
kc = read_pq('octopus_import/datasets/crops_senegal/fao56_crop_coefficients_daily.parquet')
kc['stage_enc']=LabelEncoder().fit_transform(kc['growth_stage'])
kc['crop_enc']=LabelEncoder().fit_transform(kc['crop_code'])
X_cc=kc[['crop_enc','day_after_planting','season_days','kc','kc_ini','kc_mid','kc_end']].values.astype(float)
y_cc=kc['stage_enc'].values
for mi,mn in enumerate(['LightGBM','XGBoost','CatBoost']):
    progress(f"A6 {mn}",done=mi+1,total=9)
    for fold,(tr,va) in enumerate(KFold(5,shuffle=True,random_state=42).split(X_cc)):
        if mn=='LightGBM': m=lgb.LGBMClassifier(n_estimators=500,learning_rate=0.05,max_depth=6,num_leaves=31,subsample=0.8,colsample_bytree=0.8,min_child_samples=5,verbosity=-1,n_jobs=2,callbacks=[lgb.early_stopping(30,verbose=False)])
        elif mn=='XGBoost': m=xgb.XGBClassifier(n_estimators=500,learning_rate=0.05,max_depth=6,subsample=0.8,colsample_bytree=0.8,min_child_weight=5,tree_method='hist',n_jobs=2,early_stopping_rounds=30,eval_metric='mlogloss')
        else: m=cb.CatBoostClassifier(iterations=500,learning_rate=0.05,depth=6,bootstrap_type='Bernoulli',subsample=0.8,l2_leaf_reg=3.0,verbose=0,early_stopping_rounds=30)
        bi=train_es(mn,m,X_cc[tr],y_cc[tr],X_cc[va],y_cc[va])
        all_metrics.append({'model_group':'A6_CropCalendar','model':mn,'fold':fold,
            'accuracy':round(accuracy_score(y_cc[va],m.predict(X_cc[va])),4),
            'f1_macro':round(f1_score(y_cc[va],m.predict(X_cc[va]),average='macro',zero_division=0),4),'best_iter':bi})
    sub=[x for x in all_metrics if x['model']==mn and x['model_group']=='A6_CropCalendar']
    print(f"  A6 {mn}: F1={np.mean([x['f1_macro'] for x in sub]):.4f}")

# ===== A7 NDVI =====
progress("A7",done=4,total=9)
ndvi=read_pq('octopus_import/datasets/sentinel2_ndvi/s2_ndvi_national_grid_monthly_2025.parquet')
wc=read_pq('octopus_import/datasets/crops_senegal/esa_worldcover_national_grid_0p05.parquet')
df_n=ndvi.dropna(subset=['ndvi_mean']).copy()
df_n['month_num']=pd.to_datetime(df_n['month']).dt.month
df_n['is_anomaly']=0
for mo in df_n['month_num'].unique():
    mask=df_n['month_num']==mo; vals=df_n.loc[mask,'ndvi_mean']
    df_n.loc[mask&((df_n['ndvi_mean']<vals.quantile(0.10))|(df_n['ndvi_mean']>vals.quantile(0.98))),'is_anomaly']=1
share_cols=[c for c in wc.columns if c.startswith('share_')]
df_n=df_n.merge(wc[['cell_id']+share_cols].drop_duplicates(subset=['cell_id']),on='cell_id',how='left')
feat_n=['cell_id','month_num','ndvi_mean','ndvi_std','n_valid_px','valid_fraction']+share_cols
feat_n=[f for f in feat_n if f in df_n.columns]
df_n=df_n.dropna(subset=feat_n)
X_n=df_n[feat_n].values.astype(float); y_n=df_n['is_anomaly'].values
for mi,mn in enumerate(['LightGBM','XGBoost','CatBoost']):
    progress(f"A7 {mn}",done=mi+5,total=9)
    for fold,(tr,va) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(X_n,y_n)):
        if mn=='LightGBM': m=lgb.LGBMClassifier(n_estimators=500,learning_rate=0.05,max_depth=6,num_leaves=31,subsample=0.8,colsample_bytree=0.8,min_child_samples=5,verbosity=-1,n_jobs=2,callbacks=[lgb.early_stopping(30,verbose=False)])
        elif mn=='XGBoost': m=xgb.XGBClassifier(n_estimators=500,learning_rate=0.05,max_depth=6,subsample=0.8,colsample_bytree=0.8,min_child_weight=5,tree_method='hist',n_jobs=2,early_stopping_rounds=30,eval_metric='logloss')
        else: m=cb.CatBoostClassifier(iterations=500,learning_rate=0.05,depth=6,bootstrap_type='Bernoulli',subsample=0.8,l2_leaf_reg=3.0,verbose=0,early_stopping_rounds=30)
        bi=train_es(mn,m,X_n[tr],y_n[tr],X_n[va],y_n[va])
        all_metrics.append({'model_group':'A7_NDVI_Anomaly','model':mn,'fold':fold,
            'accuracy':round(accuracy_score(y_n[va],m.predict(X_n[va])),4),
            'f1_macro':round(f1_score(y_n[va],m.predict(X_n[va]),average='macro',zero_division=0),4),'best_iter':bi})
    sub=[x for x in all_metrics if x['model']==mn and x['model_group']=='A7_NDVI_Anomaly']
    print(f"  A7 {mn}: F1={np.mean([x['f1_macro'] for x in sub]):.4f}")

# ===== A9 MARKET CLUSTERING =====
progress("A9",done=8,total=9)
prices=read_pq('octopus_import/datasets/market_prices/wfp_senegal_food_prices.parquet')
mkts=read_pq('octopus_import/datasets/market_prices/wfp_senegal_markets.parquet')
df_p=prices.copy(); df_p['price_fcfa_kg']=pd.to_numeric(df_p['price_fcfa_kg'],errors='coerce')
df_p=df_p.dropna(subset=['price_fcfa_kg'])
pivot=df_p.groupby(['market','category'])['price_fcfa_kg'].mean().reset_index()
pw=pivot.pivot_table(index='market',columns='category',values='price_fcfa_kg',fill_value=0)
lat_c=[c for c in mkts.columns if 'lat' in c.lower()]
lon_c=[c for c in mkts.columns if 'lon' in c.lower()]
if lat_c and lon_c:
    mg=mkts[['market',lat_c[0],lon_c[0]]].drop_duplicates(subset=['market'])
    mg.columns=['market','lat','lon']
    pw=pw.reset_index().merge(mg,on='market',how='left').set_index('market')
    pw['lat']=pd.to_numeric(pw['lat'],errors='coerce').fillna(0)
    pw['lon']=pd.to_numeric(pw['lon'],errors='coerce').fillna(0)
X_mkt=pw.values.astype(float); X_sc=StandardScaler().fit_transform(X_mkt)

# Only KMeans (contiguous labels guaranteed, no tiny clusters)
cr=[]
for k in range(2,8):
    lab=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(X_sc)
    sizes=np.bincount(lab)
    cr.append({'algorithm':'KMeans','k':k,'silhouette':round(silhouette_score(X_sc,lab),4),
               'min_size':int(sizes.min()),'max_size':int(sizes.max())})
    print(f"  KMeans k={k}: sil={cr[-1]['silhouette']:.4f} sizes={sizes.tolist()}")
cr_df=pd.DataFrame(cr)
# Pick best k where min cluster >= 3
viable = cr_df[cr_df['min_size']>=3]
if len(viable)>0:
    best=viable.loc[viable['silhouette'].idxmax()]
else:
    best=cr_df.loc[cr_df['silhouette'].idxmax()]
best_k=int(best['k'])
print(f"Best: KMeans k={best_k} sil={best['silhouette']:.4f}")
best_labels=KMeans(n_clusters=best_k,random_state=42,n_init=10).fit_predict(X_sc)

# Supervised 3-fold (no ES, simple)
for mn in ['LightGBM','XGBoost','CatBoost']:
    for fold,(tr,va) in enumerate(KFold(3,shuffle=True,random_state=42).split(X_mkt)):
        if mn=='LightGBM': m=lgb.LGBMClassifier(n_estimators=100,max_depth=4,verbosity=-1,n_jobs=2)
        elif mn=='XGBoost': m=xgb.XGBClassifier(n_estimators=100,max_depth=4,tree_method='hist',n_jobs=2,eval_metric='mlogloss')
        else: m=cb.CatBoostClassifier(iterations=100,depth=4,verbose=0)
        m.fit(X_mkt[tr],best_labels[tr])
        pred=m.predict(X_mkt[va])
        all_metrics.append({'model_group':'A9_MarketClustering','model':mn,'fold':fold,
            'accuracy':round(accuracy_score(best_labels[va],pred),4),
            'f1_macro':round(f1_score(best_labels[va],pred,average='macro',zero_division=0),4),'best_iter':0})
    sub=[x for x in all_metrics if x['model']==mn and x['model_group']=='A9_MarketClustering']
    print(f"  A9 {mn}: F1={np.mean([x['f1_macro'] for x in sub]):.4f}")

progress("Sauvegarde",done=9,total=9)
all_df=pd.DataFrame(all_metrics)
all_df.to_csv(OUTPUT/'remaining_models_all_metrics.csv',index=False)
cr_df.to_csv(OUTPUT/'market_clustering_results.csv',index=False)
pd.DataFrame({'market':pw.index,'cluster':best_labels}).to_csv(OUTPUT/'market_cluster_assignments.csv',index=False)

print("\n=== RÉSUMÉ FINAL ===")
for mg in all_df['model_group'].unique():
    sub=all_df[all_df['model_group']==mg]
    bm=sub.groupby('model')['f1_macro'].mean().idxmax()
    bf=sub.groupby('model')['f1_macro'].mean().max()
    print(f"{mg}: Champion={bm} F1={bf:.4f}")
result="A6+A7+A9 complete"

