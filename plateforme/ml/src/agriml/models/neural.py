"""Réseaux tabulaires optionnels (MLP PyTorch, MLP Keras) au format scikit-learn.

Sélection depuis la configuration : `kind: torch_mlp` ou `kind: keras_mlp`. La fabrique les place derrière le
même prétraitement que les modèles linéaires (imputation + standardisation + one-hot), ajusté dans le pli.
Sur du tabulaire, un MLP gagne rarement seul face au boosting ; il apporte surtout de la diversité à
l'ensemble (stacking / hill climbing). Arrêt précoce interne : `valid_fraction` du pli d'entraînement est mis
de côté et les meilleurs poids sont restaurés, l'OOF reste donc honnête.
PyTorch et Keras sont importés paresseusement ; absents, `backend_available` écarte le modèle.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Sequence

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.model_selection import train_test_split

from agriml._optional import require

NEURAL_BACKENDS = {"torch_mlp": "torch", "keras_mlp": "keras"}
MIN_DELTA = 1e-6
PREDICT_BATCH = 4096


def _dense(X) -> np.ndarray:
    """Matrice dense float32 (le one-hot peut produire une matrice creuse)."""
    return np.asarray(X.toarray() if hasattr(X, "toarray") else X, dtype=np.float32)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def _softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


class _NeuralBase(BaseEstimator):
    """Logique commune : découpe interne, normalisation de la cible, sorties probabilistes."""

    def __init__(self, task: str = "regression", n_classes: int | None = None, hidden: Sequence[int] = (256, 128),
                 dropout: float = 0.1, lr: float = 1e-3, weight_decay: float = 1e-5, max_epochs: int = 200,
                 batch_size: int = 256, patience: int = 15, valid_fraction: float = 0.1, seed: int = 42):
        self.task = task
        self.n_classes = n_classes
        self.hidden = hidden
        self.dropout = dropout
        self.lr = lr
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.batch_size = batch_size
        self.patience = patience
        self.valid_fraction = valid_fraction
        self.seed = seed

    @property
    def n_outputs(self) -> int:
        return int(self.n_classes or 2) if self.task == "multiclass" else 1

    def _target(self, y: np.ndarray) -> np.ndarray:
        if self.task == "regression":
            return ((y - self.y_mean_) / self.y_std_).astype(np.float32).reshape(-1, 1)
        if self.task == "binary":
            return y.astype(np.float32).reshape(-1, 1)
        return y.astype(np.int64)

    def fit(self, X, y):
        X, y = _dense(X), np.asarray(y)
        if self.task == "regression":
            self.y_mean_, self.y_std_ = float(y.mean()), float(y.std() or 1.0)
        else:
            self.classes_ = np.arange(max(self.n_outputs, 2))
        stratify = y if self.task != "regression" and np.bincount(y.astype(int)).min() >= 2 else None
        X_tr, X_ev, y_tr, y_ev = train_test_split(X, y, test_size=self.valid_fraction, random_state=self.seed,
                                                  stratify=stratify)
        self._fit_arrays(X_tr, self._target(y_tr), X_ev, self._target(y_ev))
        return self

    def _fit_arrays(self, X_tr, y_tr, X_ev, y_ev) -> None:  # pragma: no cover - abstrait
        raise NotImplementedError

    def _raw(self, X: np.ndarray) -> np.ndarray:  # pragma: no cover - abstrait
        raise NotImplementedError

    def predict(self, X) -> np.ndarray:
        if self.task == "regression":
            return self._raw(_dense(X))[:, 0] * self.y_std_ + self.y_mean_
        return np.argmax(self.predict_proba(X), axis=1)

    def predict_proba(self, X) -> np.ndarray:
        z = self._raw(_dense(X))
        if self.task == "binary":
            p = _sigmoid(z[:, 0])
            return np.column_stack([1 - p, p])
        return _softmax(z)


# --------------------------------------------------------------------------- PyTorch


def _torch_net(torch, n_in: int, hidden: Sequence[int], dropout: float, n_out: int):
    layers = []
    for width in hidden:
        layers += [torch.nn.Linear(n_in, width), torch.nn.SiLU(), torch.nn.Dropout(dropout)]
        n_in = width
    layers.append(torch.nn.Linear(n_in, n_out))
    return torch.nn.Sequential(*layers)


def _torch_loss(torch, task: str):
    if task == "regression":
        return torch.nn.MSELoss()
    return torch.nn.BCEWithLogitsLoss() if task == "binary" else torch.nn.CrossEntropyLoss()


class TorchMLP(_NeuralBase):
    """MLP PyTorch (SiLU + dropout, AdamW), arrêt précoce sur la perte de validation interne."""

    def _fit_arrays(self, X_tr, y_tr, X_ev, y_ev) -> None:
        torch = require("torch", "Le modèle torch_mlp")
        torch.manual_seed(self.seed)
        net = _torch_net(torch, X_tr.shape[1], self.hidden, self.dropout, self.n_outputs)
        opt = torch.optim.AdamW(net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        loss_fn = _torch_loss(torch, self.task)
        Xt, yt, Xe, ye = (torch.from_numpy(a) for a in (X_tr, y_tr, X_ev, y_ev))
        gen = torch.Generator().manual_seed(self.seed)
        best_loss, best_state, best_epoch, wait = math.inf, copy.deepcopy(net.state_dict()), 0, 0
        for epoch in range(1, self.max_epochs + 1):
            net.train()
            for idx in torch.randperm(len(Xt), generator=gen).split(self.batch_size):
                opt.zero_grad(set_to_none=True)
                loss_fn(net(Xt[idx]), yt[idx]).backward()
                opt.step()
            net.eval()
            with torch.no_grad():
                val = float(loss_fn(net(Xe), ye))
            if val < best_loss - MIN_DELTA:
                best_loss, best_state, best_epoch, wait = val, copy.deepcopy(net.state_dict()), epoch, 0
            else:
                wait += 1
                if wait >= self.patience:
                    break
        net.load_state_dict(best_state)
        self.net_, self.best_iteration_ = net.eval(), best_epoch

    def _raw(self, X: np.ndarray) -> np.ndarray:
        torch = require("torch", "Le modèle torch_mlp")
        with torch.no_grad():
            parts = [self.net_(torch.from_numpy(chunk)).numpy() for chunk in np.array_split(
                X, max(1, math.ceil(len(X) / PREDICT_BATCH)))]
        return np.concatenate(parts).astype(float)


# --------------------------------------------------------------------------- Keras


class KerasMLP(_NeuralBase):
    """Variante Keras 3 (backend TensorFlow, JAX ou PyTorch selon KERAS_BACKEND).

    Sérialisation : seuls les poids (tableaux numpy) sont picklés, le graphe est reconstruit au besoin,
    ce qui rend le paquet joblib indépendant de la version du format `.keras`.
    """

    def _build_keras(self, keras, n_in: int):
        layers = [keras.Input(shape=(n_in,))]
        for width in self.hidden:
            layers += [keras.layers.Dense(width, activation="silu"), keras.layers.Dropout(self.dropout)]
        layers.append(keras.layers.Dense(self.n_outputs))
        return keras.Sequential(layers)

    def _keras_loss(self, keras):
        if self.task == "regression":
            return keras.losses.MeanSquaredError()
        if self.task == "binary":
            return keras.losses.BinaryCrossentropy(from_logits=True)
        return keras.losses.SparseCategoricalCrossentropy(from_logits=True)

    def _fit_arrays(self, X_tr, y_tr, X_ev, y_ev) -> None:
        keras = require("keras", "Le modèle keras_mlp")
        keras.utils.set_random_seed(self.seed)
        model = self._build_keras(keras, X_tr.shape[1])
        model.compile(optimizer=keras.optimizers.AdamW(learning_rate=self.lr, weight_decay=self.weight_decay),
                      loss=self._keras_loss(keras))
        stop = keras.callbacks.EarlyStopping(monitor="val_loss", patience=self.patience, min_delta=MIN_DELTA,
                                             restore_best_weights=True)
        history = model.fit(X_tr, y_tr, validation_data=(X_ev, y_ev), epochs=self.max_epochs,
                            batch_size=self.batch_size, callbacks=[stop], verbose=0, shuffle=True)
        self.n_features_in_ = int(X_tr.shape[1])
        self.weights_ = [np.asarray(w) for w in model.get_weights()]
        self.best_iteration_ = int(np.argmin(history.history["val_loss"]) + 1)
        self.model_ = model

    def _raw(self, X: np.ndarray) -> np.ndarray:
        if getattr(self, "model_", None) is None:
            keras = require("keras", "Le modèle keras_mlp")
            model = self._build_keras(keras, self.n_features_in_)
            model.set_weights(self.weights_)
            self.model_ = model
        return np.asarray(self.model_.predict(X, batch_size=PREDICT_BATCH, verbose=0), dtype=float)

    def __getstate__(self) -> dict:
        state = dict(self.__dict__)
        state.pop("model_", None)
        return state


def make_neural(kind: str, task: str, n_classes: int | None, seed: int, params: dict) -> _NeuralBase:
    """Construit l'estimateur ; `hidden` peut venir du YAML sous forme de liste."""
    cls = {"torch_mlp": TorchMLP, "keras_mlp": KerasMLP}.get(kind)
    if cls is None:
        raise ValueError(f"Réseau tabulaire inconnu : {kind}")
    params = dict(params)
    if "hidden" in params:
        params["hidden"] = tuple(int(h) for h in params["hidden"])
    return cls(task=task, n_classes=n_classes, seed=seed, **params)
