"""Entraînement B4 Disease Detection (MobileNetV3-Small + tête PyTorch sur Rice Disease 4 classes)."""

import json
import sys
import time
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
PYDEPS = ROOT / ".pydeps"
if PYDEPS.exists() and str(PYDEPS) not in sys.path:
    sys.path.append(str(PYDEPS))

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


IMG_DIR = ROOT / "datasets" / "class_b" / "rice_disease" / "images"
OUT_DIR = ROOT / "models" / "disease"


class LeafDataset(Dataset):
    def __init__(self, samples: List[Tuple[Path, int]], tfm):
        self.samples = samples
        self.tfm = tfm

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        p, y = self.samples[idx]
        with Image.open(p) as im:
            im = im.convert("RGB")
            return self.tfm(im), y


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> float:
    f1s = []
    for c in range(n_classes):
        tp = int(np.sum((y_true == c) & (y_pred == c)))
        fp = int(np.sum((y_true != c) & (y_pred == c)))
        fn = int(np.sum((y_true == c) & (y_pred != c)))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1s.append((2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0)
    return float(np.mean(f1s))


def main():
    t0 = time.perf_counter()
    classes = sorted([d.name for d in IMG_DIR.iterdir() if d.is_dir()])
    class_to_idx = {c: i for i, c in enumerate(classes)}

    rng = np.random.default_rng(42)
    train_samples: List[Tuple[Path, int]] = []
    val_samples: List[Tuple[Path, int]] = []

    for c in classes:
        imgs = sorted([p for p in (IMG_DIR / c).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
        idx = rng.permutation(len(imgs))
        split = int(0.8 * len(imgs))
        for i in idx[:split]:
            train_samples.append((imgs[i], class_to_idx[c]))
        for i in idx[split:]:
            val_samples.append((imgs[i], class_to_idx[c]))

    print(f"Classes ({len(classes)}): {classes}")
    print(f"Train: {len(train_samples)} | Val: {len(val_samples)}")

    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    backbone = models.mobilenet_v3_small(weights=weights)
    backbone.classifier = nn.Identity()
    backbone.eval()

    tfm = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    def extract(samples):
        ds = LeafDataset(samples, tfm)
        dl = DataLoader(ds, batch_size=64, shuffle=False, num_workers=0)
        feats, ys = [], []
        with torch.no_grad():
            for xb, yb in dl:
                feats.append(backbone(xb).numpy())
                ys.append(yb.numpy())
        return np.vstack(feats), np.concatenate(ys)

    X_tr, y_tr = extract(train_samples)
    X_va, y_va = extract(val_samples)
    print(f"Extracted features: X_tr={X_tr.shape}, X_va={X_va.shape}")

    torch.manual_seed(42)
    in_dim = X_tr.shape[1]
    head = nn.Sequential(
        nn.Linear(in_dim, 128),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(128, len(classes)),
    )
    opt = torch.optim.AdamW(head.parameters(), lr=2e-3, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()

    X_tr_t = torch.from_numpy(X_tr).float()
    y_tr_t = torch.from_numpy(y_tr).long()
    X_va_t = torch.from_numpy(X_va).float()

    best_acc = 0.0
    best_state = None
    for epoch in range(1, 41):
        head.train()
        perm = torch.randperm(len(X_tr_t))
        for i in range(0, len(X_tr_t), 128):
            b = perm[i:i+128]
            opt.zero_grad()
            loss = crit(head(X_tr_t[b]), y_tr_t[b])
            loss.backward()
            opt.step()

        head.eval()
        with torch.no_grad():
            preds = head(X_va_t).argmax(dim=1).numpy()
            acc = float(np.mean(preds == y_va))
            if acc >= best_acc:
                best_acc = acc
                best_state = {k: v.clone() for k, v in head.state_dict().items()}

    head.load_state_dict(best_state)
    head.eval()
    with torch.no_grad():
        va_preds = head(X_va_t).argmax(dim=1).numpy()
    val_acc = round(float(np.mean(va_preds == y_va)), 4)
    val_f1 = round(macro_f1(y_va, va_preds, len(classes)), 4)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, OUT_DIR / "b4_rice_head.pt")
    meta = {
        "model_id": "B4_Disease_Detection_Rice",
        "backbone": "mobilenet_v3_small",
        "in_dim": in_dim,
        "classes": classes,
        "train_samples": len(train_samples),
        "val_samples": len(val_samples),
        "val_accuracy": val_acc,
        "val_macro_f1": val_f1,
        "train_seconds": round(time.perf_counter() - t0, 2),
    }
    (OUT_DIR / "b4_rice_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
