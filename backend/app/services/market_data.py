"""Market data engine.

Primary source: yfinance (free). Falls back to a deterministic synthetic
generator when the network is unavailable so the rest of the app keeps working.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.core.net import enable_os_trust_store

# Fix TLS against corporate SSL-inspection proxies before any HTTPS call.
enable_os_trust_store()

# Index/symbol map: friendly name -> yfinance ticker
SYMBOL_MAP: dict[str, dict] = {
    "NIFTY": {"yf": "^NSEI", "name": "NIFTY 50", "lot": 50},
    "BANKNIFTY": {"yf": "^NSEBANK", "name": "NIFTY BANK", "lot": 15},
    "FINNIFTY": {"yf": "NIFTY_FIN_SERVICE.NS", "name": "NIFTY FIN SERVICE", "lot": 40},
    "SENSEX": {"yf": "^BSESN", "name": "BSE SENSEX", "lot": 10},
    "RELIANCE": {"yf": "RELIANCE.NS", "name": "Reliance Industries", "lot": 250},
    "TCS": {"yf": "TCS.NS", "name": "Tata Consultancy", "lot": 175},
    "HDFCBANK": {"yf": "HDFCBANK.NS", "name": "HDFC Bank", "lot": 550},
    "INFY": {"yf": "INFY.NS", "name": "Infosys", "lot": 400},
}

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 20  # seconds — keeps quotes fresh during market hours

# Freshest spot price per ticker from the chart `meta` block (updates more often
# than the 15m candle close). Populated on every successful fetch.
_quote_meta: dict[str, dict] = {}

# Tracks whether the most recent fetch per ticker was real ("live") or the
# synthetic fallback ("demo"). Keyed by full cache key (ticker:period:interval)
# so a successful short-range fetch can't mask a failed long-range one.
_source: dict[str, str] = {}


def data_source(symbol: str | None = None, period: str = "60d", interval: str = "15m") -> str:
    """Return 'live' if the fetch for this exact series hit a real provider, else 'demo'.

    With no symbol, returns 'live' only if EVERY tracked series is currently live.
    Defaults to the 60d/15m series that the signal engine actually uses.
    """
    if symbol is not None:
        ckey = f"hist:{resolve(symbol)['yf']}:{period}:{interval}"
        return _source.get(ckey, "demo")
    return "live" if _source and all(v == "live" for v in _source.values()) else "demo"


def resolve(symbol: str) -> dict:
    key = symbol.upper().strip()
    if key in SYMBOL_MAP:
        return {"key": key, **SYMBOL_MAP[key]}
    # Treat as raw NSE equity ticker
    yf = key if key.endswith(".NS") or key.startswith("^") else f"{key}.NS"
    return {"key": key, "yf": yf, "name": key, "lot": 1}


def _cached(key: str):
    hit = _cache.get(key)
    if hit and (time.time() - hit[0]) < _CACHE_TTL:
        return hit[1]
    return None


def _store(key: str, value):
    _cache[key] = (time.time(), value)
    return value


def _synthetic_history(seed_symbol: str, days: int, interval: str) -> pd.DataFrame:
    """Deterministic geometric-brownian-ish series for offline/dev mode."""
    rng = np.random.default_rng(abs(hash(seed_symbol)) % (2**32))
    n = max(days * (75 if interval.endswith("m") else 1), 120)
    base = 20000 + (abs(hash(seed_symbol)) % 5000)
    rets = rng.normal(0.0003, 0.01, n)
    close = base * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = rng.integers(1e5, 5e6, n).astype(float)
    idx = pd.date_range(end=datetime.now(timezone.utc), periods=n, freq="15min" if interval.endswith("m") else "D")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx
    )


def _period_to_days(period: str) -> int:
    p = period.strip().lower()
    if p.endswith("mo"):
        return int(p[:-2] or 1) * 30
    if p.endswith("d"):
        return int(p[:-1] or 60)
    if p.endswith("y"):
        return int(p[:-1] or 1) * 365
    return 60


def _yahoo_range(period: str, interval: str) -> str:
    """Map a requested period to a valid Yahoo `range` enum.

    Yahoo's chart API rejects arbitrary period1/period2 spans for intraday
    intervals (e.g. 60 days of 15m -> HTTP 422). Only the fixed range enum
    (1d,5d,1mo,3mo,6mo,1y,2y,5y,max) is reliable; intraday is capped near 60d.
    """
    days = _period_to_days(period)
    if interval.endswith("m") or interval.endswith("h"):
        return "5d" if days <= 5 else "1mo"  # ~550 15m bars: ample for EMA200
    if days <= 5:
        return "5d"
    if days <= 31:
        return "1mo"
    if days <= 93:
        return "3mo"
    if days <= 186:
        return "6mo"
    if days <= 366:
        return "1y"
    return "2y"


def _fetch_yahoo_chart(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    """Fetch OHLCV straight from Yahoo's v8 chart API.

    yfinance's bundled crumb/cookie flow breaks against current Yahoo; the public
    chart endpoint works directly and is far more robust behind proxies.
    """
    import httpx

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": _yahoo_range(period, interval), "interval": interval, "includePrePost": "false"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # Retry transient errors (429/5xx) with backoff; range-based requests are
    # otherwise reliable so this rarely fires.
    for attempt in range(3):
        try:
            with httpx.Client(headers=headers, timeout=12.0) as client:
                r = client.get(url, params=params)
                if r.status_code in (429, 422):
                    raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
                r.raise_for_status()
                data = r.json()
            result = (data.get("chart", {}).get("result") or [None])[0]
            if not result:
                return None
            meta = result.get("meta") or {}
            if meta.get("regularMarketPrice") is not None:
                _quote_meta[ticker] = {
                    "price": float(meta["regularMarketPrice"]),
                    "prev_close": float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0) or None,
                    "time": meta.get("regularMarketTime"),
                }
            ts = result.get("timestamp")
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            if not ts or not quote.get("close"):
                return None
            idx = pd.to_datetime(ts, unit="s", utc=True)
            df = pd.DataFrame(
                {
                    "Open": quote.get("open"),
                    "High": quote.get("high"),
                    "Low": quote.get("low"),
                    "Close": quote.get("close"),
                    "Volume": quote.get("volume"),
                },
                index=idx,
            ).dropna()
            return df if not df.empty else None
        except Exception:
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))  # 0.6s, 1.2s backoff
                continue
            return None


def get_history(symbol: str, period: str = "60d", interval: str = "15m") -> pd.DataFrame:
    info = resolve(symbol)
    ckey = f"hist:{info['yf']}:{period}:{interval}"
    cached = _cached(ckey)
    if cached is not None:
        return cached

    df = _fetch_yahoo_chart(info["yf"], period, interval)

    if df is None or len(df) < 30:
        days = 60 if period.endswith("d") else 120
        df = _synthetic_history(info["yf"], days, interval)
        _source[ckey] = "demo"
    else:
        _source[ckey] = "live"

    return _store(ckey, df)


def get_quote(symbol: str) -> dict:
    info = resolve(symbol)
    # Reuse a richer cached series (the signal engine's 60d/15m) when present so a
    # quote doesn't fire a second Yahoo request and risk a rate-limited fallback.
    ckey60 = f"hist:{info['yf']}:60d:15m"
    cached60 = _cached(ckey60)
    if cached60 is not None:
        df, src_key = cached60, ckey60
    else:
        df = get_history(symbol, period="5d", interval="15m")
        src_key = f"hist:{info['yf']}:5d:15m"
    last = float(df["Close"].iloc[-1])
    # prev close = close of previous day's last bar (approx)
    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else last
    # Prefer the live spot price from chart meta — fresher than the last candle.
    meta = _quote_meta.get(info["yf"])
    if meta and _source.get(src_key) == "live":
        last = meta["price"]
        prev = meta.get("prev_close") or prev
    day = df.tail(min(len(df), 25))
    change = last - prev
    return {
        "symbol": info["key"],
        "name": info["name"],
        "last_price": round(last, 2),
        "change": round(change, 2),
        "change_pct": round((change / prev) * 100, 2) if prev else 0.0,
        "open": round(float(day["Open"].iloc[0]), 2),
        "high": round(float(day["High"].max()), 2),
        "low": round(float(day["Low"].min()), 2),
        "prev_close": round(prev, 2),
        "volume": float(day["Volume"].sum()),
        "source": _source.get(src_key, "demo"),
        "timestamp": datetime.now(timezone.utc),
    }


def get_candles(symbol: str, period: str = "60d", interval: str = "15m") -> list[dict]:
    df = get_history(symbol, period=period, interval=interval)
    out = []
    for ts, row in df.tail(300).iterrows():
        out.append({
            "time": ts.strftime("%Y-%m-%d %H:%M") if interval.endswith("m") else ts.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": float(row["Volume"]),
        })
    return out


def list_symbols() -> list[dict]:
    return [{"symbol": k, "name": v["name"], "lot": v["lot"]} for k, v in SYMBOL_MAP.items()]
