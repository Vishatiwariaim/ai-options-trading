"""ML inference service.

Loads trained artifacts from ml/artifacts/ when present and produces multi-horizon
bullish/bearish probabilities. If no models are trained yet, it gracefully derives a
probability from the rule-based signal score so the API always responds.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from app.services import market_data
from ml.features import build_feature_row

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "ml" / "artifacts"

_loaded: dict = {}


def _load_models():
    global _loaded
    if _loaded:
        return _loaded
    models = {}
    try:
        import joblib

        for name in ("xgboost", "random_forest"):
            p = ARTIFACT_DIR / f"{name}.joblib"
            if p.exists():
                models[name] = joblib.load(p)
        scaler_p = ARTIFACT_DIR / "scaler.joblib"
        if scaler_p.exists():
            models["scaler"] = joblib.load(scaler_p)
    except Exception:
        pass

    # LSTM (optional / heavy)
    try:
        lstm_p = ARTIFACT_DIR / "lstm.keras"
        if lstm_p.exists():
            from tensorflow import keras

            models["lstm"] = keras.models.load_model(lstm_p)
    except Exception:
        pass

    _loaded = models
    return models


def _rule_fallback(symbol: str) -> float:
    from app.services import signal_engine

    score = signal_engine.generate(symbol)["score"]
    return round(score / 100.0, 4)  # 0..1 bullish prob


def predict(symbol: str) -> dict:
    models = _load_models()
    horizons = ["5min", "15min", "1hour", "intraday", "swing"]

    if not any(k in models for k in ("xgboost", "random_forest", "lstm")):
        base = _rule_fallback(symbol)
        # de-rate confidence over longer horizons
        damp = {"5min": 1.0, "15min": 0.97, "1hour": 0.92, "intraday": 0.88, "swing": 0.82}
        preds = {}
        for h in horizons:
            p = 0.5 + (base - 0.5) * damp[h]
            preds[h] = {"bullish": round(p * 100, 1), "bearish": round((1 - p) * 100, 1)}
        return {
            "symbol": symbol.upper(),
            "source": "rule-based-fallback",
            "note": "No trained ML models found. Run `python -m ml.train` to enable XGBoost/RF/LSTM.",
            "predictions": preds,
        }

    df = market_data.get_history(symbol, period="120d", interval="1d")
    feats = build_feature_row(df)
    X = np.array(feats["vector"]).reshape(1, -1)
    if "scaler" in models:
        X = models["scaler"].transform(X)

    probs = []
    used = []
    for name in ("xgboost", "random_forest"):
        if name in models:
            p = float(models[name].predict_proba(X)[0][1])
            probs.append(p)
            used.append(name)

    if "lstm" in models:
        try:
            seq = build_feature_row(df, sequence=True)["sequence"]
            arr = np.array(seq).reshape(1, len(seq), -1)
            p = float(models["lstm"].predict(arr, verbose=0)[0][0])
            probs.append(p)
            used.append("lstm")
        except Exception:
            pass

    ensemble = float(np.mean(probs)) if probs else _rule_fallback(symbol)
    damp = {"5min": 0.96, "15min": 1.0, "1hour": 0.95, "intraday": 0.9, "swing": 0.85}
    preds = {}
    for h in horizons:
        p = 0.5 + (ensemble - 0.5) * damp[h]
        preds[h] = {"bullish": round(p * 100, 1), "bearish": round((1 - p) * 100, 1)}

    return {
        "symbol": symbol.upper(),
        "source": "ensemble:" + "+".join(used),
        "note": "Probabilistic ML output. Not financial advice.",
        "predictions": preds,
    }
