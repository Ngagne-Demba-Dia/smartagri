"""Entraînement vision par plis (StratifiedGroupKFold par plante) : AMP, OneCycle, Mixup/CutMix, EMA, TTA.

Usage :
    python -m agriml.vision.train_vision --config configs/vision_disease.yaml [--epochs 1] [--max-folds 1]
                                         [--image-size 96] [--no-export]

Artefacts (`artifacts/<name>/`) : oof.csv (probabilités hors-pli), cv_scores.json, fold<k>_ema.pt,
model.onnx (si l'export réussit) + parité onnxruntime, config_resolved.yaml.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import time
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from torch import nn
from torch.optim.swa_utils import update_bn

from agriml.io import write_json
from agriml.logs import setup_logging
from agriml.metrics import get_metric
from agriml.vision.augment import mix_batch, soft_cross_entropy, soft_targets
from agriml.vision.config import VisionConfig
from agriml.vision.data import make_loader
from agriml.vision.export import export_and_check
from agriml.vision.folds import load_metadata, make_folds
from agriml.vision.model import ModelEMA, create_model

logger = logging.getLogger("agriml.vision.train_vision")
REPORT_METRICS = ("accuracy", "f1_macro", "logloss")


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def train_one_epoch(model: nn.Module, ema: ModelEMA, loader, optimizer, scheduler, scaler, cfg: VisionConfig,
                    rng: np.random.Generator, device: torch.device) -> float:
    model.train()
    amp = cfg.amp and device.type == "cuda"
    losses = []
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        targets = soft_targets(y, len(cfg.classes), cfg.label_smoothing)
        x, targets = mix_batch(x, targets, rng, cfg.mixup_alpha, cfg.cutmix_alpha, cfg.mix_prob)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
            loss = soft_cross_entropy(model(x), targets)
        optimizer.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        ema.update(model)
        losses.append(float(loss.detach()))
    return float(np.mean(losses)) if losses else float("nan")


@torch.no_grad()
def predict_proba(model: nn.Module, loader, device: torch.device, tta: bool = True) -> np.ndarray:
    """Probabilités ; TTA = moyenne image / miroir horizontal (symétrie naturelle d'une feuille)."""
    model.eval()
    out = []
    for x, _ in loader:
        x = x.to(device)
        logits = model(x).float().softmax(-1)
        if tta:
            logits = (logits + model(torch.flip(x, dims=[3])).float().softmax(-1)) / 2
        out.append(logits.cpu().numpy())
    return np.concatenate(out) if out else np.empty((0, 0))


def recalibrate_bn(model: nn.Module, loader, device: torch.device) -> None:
    """Recalcule les statistiques BatchNorm (moyenne cumulée) sur le pli d'entraînement non augmenté.

    Indispensable pour les poids EMA (moyennés sans leurs statistiques) et pour les entraînements courts :
    MobileNetV3 utilise un momentum BN de 0,01, ses statistiques restent sinon proches de l'initialisation.
    """
    update_bn(loader, model, device=device)


def score_all(y: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    return {name: float(get_metric(name)(y, proba)) for name in REPORT_METRICS}


def _optimizer(model: nn.Module, cfg: VisionConfig, steps_per_epoch: int):
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=cfg.lr, epochs=cfg.epochs,
                                                    steps_per_epoch=max(steps_per_epoch, 1), pct_start=0.2)
    return optimizer, scheduler


def train_fold(cfg: VisionConfig, meta: pd.DataFrame, folds: np.ndarray, k: int,
               device: torch.device) -> tuple[np.ndarray, dict[str, Any], ModelEMA]:
    torch.manual_seed(cfg.seed + k)
    rng = np.random.default_rng(cfg.seed + k)
    tr_loader = make_loader(cfg, meta[folds != k], train=True)
    va_loader = make_loader(cfg, meta[folds == k], train=False)
    model, backend = create_model(cfg, len(cfg.classes))
    model = model.to(device)
    ema = ModelEMA(model, cfg.ema_decay)
    optimizer, scheduler = _optimizer(model, cfg, len(tr_loader))
    scaler = torch.amp.GradScaler(device.type, enabled=cfg.amp and device.type == "cuda")
    for epoch in range(cfg.epochs):
        loss = train_one_epoch(model, ema, tr_loader, optimizer, scheduler, scaler, cfg, rng, device)
        logger.info("pli %d époque %d/%d : perte %.4f", k, epoch + 1, cfg.epochs, loss)
    calib_loader = make_loader(cfg, meta[folds != k], train=False)
    for net in (model, ema.module):
        recalibrate_bn(net, calib_loader, device)
    y_va = meta.loc[folds == k, "target"].to_numpy()
    raw = score_all(y_va, predict_proba(model, va_loader, device, cfg.tta))
    proba = predict_proba(ema.module, va_loader, device, cfg.tta)
    report = {"backend": backend, "n_train": int((folds != k).sum()), "n_valid": int(len(y_va)),
              "raw_model": raw, "ema": score_all(y_va, proba)}
    return proba, report, ema


def run_vision(cfg: VisionConfig, max_folds: int | None = None, export: bool = True) -> dict[str, Any]:
    device = _device()
    run_dir = cfg.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config_resolved.yaml").write_text(yaml.safe_dump(dataclasses.asdict(cfg), allow_unicode=True),
                                                   encoding="utf-8")
    meta = load_metadata(cfg)
    folds = make_folds(meta, cfg)
    selected = list(cfg.folds or range(cfg.n_splits))[: max_folds or None]
    oof = np.full((len(meta), len(cfg.classes)), np.nan)
    reports, t0, last_ema = {}, time.perf_counter(), None
    for k in selected:
        proba, reports[f"fold{k}"], last_ema = train_fold(cfg, meta, folds, k, device)
        oof[folds == k] = proba
        torch.save(last_ema.module.state_dict(), run_dir / f"fold{k}_ema.pt")
    done = ~np.isnan(oof).any(axis=1)
    payload = {"experiment": cfg.name, "device": device.type, "folds": selected, "per_fold": reports,
               "oof": score_all(meta["target"].to_numpy()[done], oof[done]), "n_oof": int(done.sum()),
               "seconds": round(time.perf_counter() - t0, 1)}
    proba_cols = {f"proba_{c}": oof[:, i] for i, c in enumerate(cfg.classes)}
    meta.assign(fold=folds, **proba_cols).to_csv(run_dir / "oof.csv", index=False)
    if export and last_ema is not None:
        result = export_and_check(last_ema.module.cpu(), run_dir / "model.onnx", cfg.image_size)
        payload["onnx"] = dataclasses.asdict(result)
    write_json(payload, run_dir / "cv_scores.json")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Entraînement vision agriml (classification de maladies).")
    parser.add_argument("--config", required=True)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--max-folds", type=int)
    parser.add_argument("--image-size", type=int)
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    cfg = VisionConfig.from_yaml(args.config)
    overrides = {k: v for k, v in {"epochs": args.epochs, "image_size": args.image_size}.items() if v}
    cfg = dataclasses.replace(cfg, **overrides)
    payload = run_vision(cfg, args.max_folds, export=not args.no_export)
    logger.info("OOF %s sur %d images en %.0f s", payload["oof"], payload["n_oof"], payload["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
