from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

ART = Path(__file__).resolve().parent / "artifacts"
BUNDLE = ART / "cost_bundle.joblib"
_cache = None


def _load():
    global _cache
    if _cache is None:
        if not BUNDLE.exists():
            raise FileNotFoundError("Model bundle not trained")
        _cache = joblib.load(BUNDLE)
    return _cache


def predict_additional_ratio(department: str, los: int, severity: str = "Medium") -> float:
    b = _load()
    enc = b["encoder"]
    X = enc.transform([[department, severity]])
    from scipy import sparse

    X = sparse.hstack([X, np.array([[los]])]).tocsr()
    pred = float(b["ratio_model"].predict(X)[0])
    return float(np.clip(pred, 0.85, 1.35))


def predict_los(department: str, severity: str = "Medium") -> float:
    b = _load()
    enc = b["encoder"]
    X = enc.transform([[department, severity]])
    pred = float(b["los_model"].predict(X)[0])
    return float(np.clip(pred, 1, 21))
