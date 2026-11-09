"""Génère (et exécute en option) le carnet d'EDA « grandmaster » : notebooks/01_eda.ipynb.

Le carnet suit la checklist de docs/08_competition_ia.md : forme et types, valeurs manquantes, cible,
groupes et temps, audit de fuite (identifiants partagés, doublons, variables trop corrélées à la cible),
validation adversariale train/test. Les données par défaut sont SYNTHÉTIQUES (scripts/make_synthetic.py).

    python scripts/build_eda_notebook.py                      # écrit le carnet
    python scripts/build_eda_notebook.py --execute            # + notebooks/01_eda.executed.ipynb (ignoré par Git)
"""

from __future__ import annotations

import argparse
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ML_ROOT / "notebooks" / "01_eda.ipynb"
EXEC_TIMEOUT_S = 600

SETUP = '''import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ML_ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.insert(0, str(ML_ROOT / "src"))
from agriml.adversarial import adversarial_validation
DATA = ML_ROOT / "{data_dir}"
TARGET, GROUP, TIME, ID = "{target}", "{group}", "{time}", "{id_col}"
train = pd.read_csv(DATA / "{train}")
test = pd.read_csv(DATA / "{test}")
print(train.shape, test.shape)'''

CELLS = [
    ("md", "# EDA — {title}\n\nDonnées **{origin}**. Checklist : docs/08_competition_ia.md §2 (EDA) et §3 (fuites)."),
    ("code", SETUP),
    ("md", "## 1. Forme, types, valeurs manquantes"),
    ("code", "summary = pd.DataFrame({'dtype': train.dtypes.astype(str), 'na_train': train.isna().mean(),\n"
             "                        'na_test': test.reindex(columns=train.columns).isna().mean(),\n"
             "                        'n_unique': train.nunique()})\nsummary.sort_values('na_train', ascending=False).head(20)"),
    ("md", "## 2. Cible : distribution, asymétrie, valeurs extrêmes"),
    ("code", "print(train[TARGET].describe())\nprint('asymétrie', round(train[TARGET].skew(), 3))\n"
             "ax = train[TARGET].hist(bins=40); ax.set_title(TARGET); plt.close()"),
    ("md", "## 3. Groupes et temps : choix du schéma de validation croisée"),
    ("code", "print('groupes train', train[GROUP].nunique(), '| test', test[GROUP].nunique(),\n"
             "      '| partagés', len(set(train[GROUP]) & set(test[GROUP])))\n"
             "print('périodes train', sorted(train[TIME].unique())[-3:], '| test', sorted(test[TIME].unique()))\n"
             "train.groupby(TIME)[TARGET].agg(['mean', 'std', 'count']).tail(10)"),
    ("md", "## 4. Audit de fuite\n\nIdentifiants communs, doublons, variables quasi égales à la cible."),
    ("code", "print('ID communs train/test :', len(set(train[ID]) & set(test[ID])))\n"
             "feats = [c for c in train.columns if c not in (TARGET, ID)]\n"
             "print('doublons (hors ID/cible) :', int(train.duplicated(subset=feats).sum()))\n"
             "num = train.select_dtypes('number').drop(columns=[TARGET], errors='ignore')\n"
             "corr = num.corrwith(train[TARGET]).abs().sort_values(ascending=False)\n"
             "suspects = corr[corr > 0.95]\nprint('corrélation |r| > 0.95 :', list(suspects.index))\ncorr.head(10)"),
    ("md", "## 5. Validation adversariale train/test\n\nAUC ≈ 0,5 : distributions proches ; > 0,7 : "
           "dérive à traiter (pondération, retrait de variables, CV qui imite le test)."),
    ("code", "# la colonne temps sépare trivialement train et test (AUC = 1) : on l'exclut de la comparaison\n"
             "cols = [c for c in num.columns if c in test.columns and c not in (ID, TIME)]\n"
             "adv = adversarial_validation(train, test, cols, n_splits=5)\n"
             "print('AUC adversariale', round(adv.auc, 4))\npd.DataFrame(adv.top_features, columns=['variable', 'importance'])"),
]

DATASETS = {
    "yield": {"title": "rendement (t/ha)", "data_dir": "data/synthetic/yield", "train": "yield_train.csv",
              "test": "yield_test.csv", "target": "yield_t_ha", "group": "field_id", "time": "year",
              "id_col": "row_id", "origin": "SYNTHÉTIQUES"},
}


def build_notebook(dataset: str = "yield"):
    """Construit l'objet carnet (nbformat v4) sans l'exécuter."""
    import nbformat

    params = DATASETS[dataset]
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for kind, text in CELLS:
        # seuls le Markdown et la cellule d'initialisation portent des gabarits ({...}) ; le code reste brut
        source = text.format(**params) if kind == "md" or text is SETUP else text
        cell = nbformat.v4.new_markdown_cell(source) if kind == "md" else nbformat.v4.new_code_cell(source)
        nb.cells.append(cell)
    return nb


def execute_notebook(nb, workdir: Path, timeout_s: int = EXEC_TIMEOUT_S):
    """Exécute le carnet avec le noyau python3 local (nbclient) et renvoie le carnet exécuté."""
    from nbclient import NotebookClient

    NotebookClient(nb, timeout=timeout_s, kernel_name="python3", resources={"metadata": {"path": str(workdir)}}).execute()
    return nb


def main(argv: list[str] | None = None) -> int:
    import nbformat

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="yield")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    nb = build_notebook(args.dataset)
    nbformat.write(nb, out)
    print(f"carnet ecrit : {out}")
    if args.execute:
        executed = execute_notebook(nb, ML_ROOT)
        target = out.with_name(out.stem + ".executed.ipynb")
        nbformat.write(executed, target)
        print(f"carnet execute : {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
