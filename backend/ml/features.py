"""Feature engineering shared between training and inference.

Keeping this in one place guarantees the exact same columns are produced at
train time and at predict time (a classic source of ML bugs).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services import indicators

FEATURE_COLUMNS = [
    "ret1", "ret5", "rsi", "macd_hist", "vwap_dist",
    "ema20_dist", "ema50_dist", "ema200_dist", "atr_pct",
    "bb_pos", "supertrend", "vol_z",
]


def _frame_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]
    macd_line, _, hist = indicators.macd(close)
    bb_up, bb_mid, bb_low = indicators.bollinger(close)
    _vwap = indicators.vwap(df)
    _atr = indicators.atr(df)

    out = pd.DataFrame(index=df.index)
    out["ret1"] = close.pct_change(1)
    out["ret5"] = close.pct_change(5)
    out["rsi"] = indicators.rsi(close) / 100.0
    out["macd_hist"] = hist / close
    out["vwap_dist"] = (close - _vwap) / close
    out["ema20_dist"] = (close - indicators.ema(close, 20)) / close
    out["ema50_dist"] = (close - indicators.ema(close, 50)) / close
    out["ema200_dist"] = (close - indicators.ema(close, 200)) / close
    out["atr_pct"] = _atr / close
    rng = (bb_up - bb_low).replace(0, np.nan)
    out["bb_pos"] = (close - bb_low) / rng
    out["supertrend"] = indicators.supertrend(df)
    vol = df["Volume"]
    out["vol_z"] = (vol - vol.rolling(20).mean()) / vol.rolling(20).std()
    return out[FEATURE_COLUMNS]


def build_training_frame(df: pd.DataFrame, horizon: int = 5) -> tuple[pd.DataFrame, pd.Series]:
    """Features X and binary label y (1 if price up after `horizon` bars)."""
    feats = _frame_features(df)
    future_ret = df["Close"].shift(-horizon) / df["Close"] - 1
    label = (future_ret > 0).astype(int)
    data = feats.copy()
    data["__label__"] = label
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    y = data.pop("__label__")
    return data, y


def build_feature_row(df: pd.DataFrame, sequence: bool = False) -> dict:
    feats = _frame_features(df).replace([np.inf, -np.inf], np.nan).ffill().fillna(0)
    if sequence:
        seq = feats.tail(30).values.tolist()
        return {"sequence": seq, "columns": FEATURE_COLUMNS}
    return {"vector": feats.iloc[-1].tolist(), "columns": FEATURE_COLUMNS}
