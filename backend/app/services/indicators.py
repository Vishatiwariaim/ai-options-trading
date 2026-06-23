"""Technical indicators implemented with pandas/numpy (no native TA-Lib needed)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_vol = df["Volume"].cumsum().replace(0, np.nan)
    return (tp * df["Volume"]).cumsum() / cum_vol


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Average Directional Index — trend strength (not direction). >25 = trending."""
    h, l, c = df["High"], df["Low"], df["Close"]
    up = h.diff()
    down = -l.diff()
    plus_dm = ((up > down) & (up > 0)) * up.clip(lower=0)
    minus_dm = ((down > up) & (down > 0)) * down.clip(lower=0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_w = tr.ewm(alpha=1 / length, adjust=False).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr_w
    minus_di = 100 * minus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr_w
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / length, adjust=False).mean().fillna(0)


def bollinger(series: pd.Series, length: int = 20, mult: float = 2.0):
    mid = series.rolling(length).mean()
    std = series.rolling(length).std()
    return mid + mult * std, mid, mid - mult * std


def supertrend(df: pd.DataFrame, length: int = 10, mult: float = 3.0) -> pd.Series:
    _atr = atr(df, length)
    hl2 = (df["High"] + df["Low"]) / 2
    upper = hl2 + mult * _atr
    lower = hl2 - mult * _atr
    direction = pd.Series(1, index=df.index)
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
    return direction  # 1 = uptrend, -1 = downtrend


def compute_all(df: pd.DataFrame) -> dict:
    """Return the latest snapshot of all indicators."""
    close = df["Close"]
    macd_line, signal_line, hist = macd(close)
    bb_up, bb_mid, bb_low = bollinger(close)
    st = supertrend(df)
    _vwap = vwap(df)

    def last(s):
        v = s.iloc[-1]
        return None if pd.isna(v) else round(float(v), 2)

    return {
        "close": last(close),
        "rsi": last(rsi(close)),
        "macd": last(macd_line),
        "macd_signal": last(signal_line),
        "macd_hist": last(hist),
        "vwap": last(_vwap),
        "ema20": last(ema(close, 20)),
        "ema50": last(ema(close, 50)),
        "ema200": last(ema(close, 200)),
        "atr": last(atr(df)),
        "adx": last(adx(df)),
        "bb_upper": last(bb_up),
        "bb_mid": last(bb_mid),
        "bb_lower": last(bb_low),
        "supertrend": int(st.iloc[-1]),
    }
