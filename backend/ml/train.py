"""Train ML models on real historical data (free via yfinance).

Usage:
    python -m ml.train --symbol ^NSEI --models all
    python -m ml.train --symbol ^NSEBANK --models xgboost,random_forest
    python -m ml.train --symbol RELIANCE.NS --models all --horizon 5

Models:
    random_forest  scikit-learn RandomForestClassifier
    xgboost        XGBClassifier
    lstm           Keras LSTM (requires `pip install tensorflow`)

Artifacts are saved to ml/artifacts/ and auto-loaded by the prediction API.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from app.services import market_data
from ml.features import build_training_frame, FEATURE_COLUMNS

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def _load_data(symbol: str) -> "pd.DataFrame":  # noqa: F821
    print(f"[data] downloading history for {symbol} ...")
    df = market_data.get_history(symbol, period="720d", interval="1d")
    print(f"[data] {len(df)} rows")
    return df


def _split(X, y, test_frac=0.2):
    n = len(X)
    cut = int(n * (1 - test_frac))
    return X[:cut], X[cut:], y[:cut], y[cut:]


def train_sklearn(name, model, Xtr, Xte, ytr, yte, scaler):
    from sklearn.metrics import accuracy_score, roc_auc_score
    import joblib

    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    proba = model.predict_proba(Xte)[:, 1]
    acc = accuracy_score(yte, pred)
    try:
        auc = roc_auc_score(yte, proba)
    except ValueError:
        auc = float("nan")
    print(f"[{name}] accuracy={acc:.3f}  auc={auc:.3f}")
    joblib.dump(model, ARTIFACT_DIR / f"{name}.joblib")
    joblib.dump(scaler, ARTIFACT_DIR / "scaler.joblib")
    return acc


def train_lstm(df, horizon, scaler):
    try:
        from tensorflow import keras
        from tensorflow.keras import layers
    except Exception as e:
        print(f"[lstm] skipped (tensorflow not installed): {e}")
        return None

    from ml.features import _frame_features

    feats = _frame_features(df).replace([np.inf, -np.inf], np.nan).dropna()
    future_ret = df["Close"].shift(-horizon) / df["Close"] - 1
    label = (future_ret > 0).astype(int).reindex(feats.index)
    arr = scaler.transform(feats.values)

    seq_len = 30
    X, y = [], []
    labels = label.values
    for i in range(seq_len, len(arr)):
        X.append(arr[i - seq_len:i])
        y.append(labels[i])
    X, y = np.array(X), np.array(y)
    mask = ~np.isnan(y)
    X, y = X[mask], y[mask]
    if len(X) < 60:
        print("[lstm] not enough data, skipped")
        return None

    cut = int(len(X) * 0.8)
    Xtr, Xte, ytr, yte = X[:cut], X[cut:], y[:cut], y[cut:]

    model = keras.Sequential([
        layers.Input(shape=(seq_len, len(FEATURE_COLUMNS))),
        layers.LSTM(48, return_sequences=True),
        layers.Dropout(0.2),
        layers.LSTM(24),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(Xtr, ytr, validation_data=(Xte, yte), epochs=25, batch_size=32, verbose=2)
    model.save(ARTIFACT_DIR / "lstm.keras")
    print("[lstm] saved lstm.keras")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="^NSEI", help="yfinance ticker or NIFTY/BANKNIFTY/...")
    ap.add_argument("--models", default="all", help="comma list: random_forest,xgboost,lstm or 'all'")
    ap.add_argument("--horizon", type=int, default=5, help="bars ahead to predict direction")
    args = ap.parse_args()

    wanted = {"random_forest", "xgboost", "lstm"} if args.models == "all" else set(args.models.split(","))

    df = _load_data(args.symbol)
    X, y = build_training_frame(df, horizon=args.horizon)
    if len(X) < 100:
        print("Not enough data to train. Try a longer-history symbol.")
        sys.exit(1)
    print(f"[features] {X.shape[0]} samples, {X.shape[1]} features, "
          f"label balance up={y.mean():.2f}")

    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(X.values)
    Xs = scaler.transform(X.values)
    Xtr, Xte, ytr, yte = _split(Xs, y.values)

    if "random_forest" in wanted:
        from sklearn.ensemble import RandomForestClassifier

        train_sklearn(
            "random_forest",
            RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=20,
                                   random_state=42, n_jobs=-1),
            Xtr, Xte, ytr, yte, scaler,
        )

    if "xgboost" in wanted:
        try:
            from xgboost import XGBClassifier

            train_sklearn(
                "xgboost",
                XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.03,
                              subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                              random_state=42),
                Xtr, Xte, ytr, yte, scaler,
            )
        except Exception as e:
            print(f"[xgboost] skipped: {e}")

    if "lstm" in wanted:
        train_lstm(df, args.horizon, scaler)

    print(f"\nDone. Artifacts in {ARTIFACT_DIR}")
    print("The prediction API will auto-load them on next request.")


if __name__ == "__main__":
    main()
