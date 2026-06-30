"""Upstox data provider — REAL option chain (PCR / OI / Max-Pain inputs).

Enables accurate option analytics that NSE blocks for free. Requires an Upstox
developer app + a daily access token (expires 3:30 AM IST). Get a token with:
    python -m scripts.upstox_login

The token is read from (in order): settings.upstox_access_token (env), or the
file backend/.upstox_token.json written by the login helper.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime
from pathlib import Path

import httpx

from app.core.config import settings

_BASE = "https://api.upstox.com/v2"
_TOKEN_FILE = Path(__file__).resolve().parents[2] / ".upstox_token.json"

# Friendly symbol -> Upstox underlying instrument_key (index options).
INSTRUMENT_KEYS: dict[str, str] = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
    "SENSEX": "BSE_INDEX|SENSEX",
}

_cache: dict[str, tuple[float, object]] = {}
_TTL = 60


def access_token() -> str | None:
    """Resolve the Upstox access token from env or the saved token file."""
    if settings.upstox_access_token:
        return settings.upstox_access_token
    try:
        if _TOKEN_FILE.exists():
            data = json.loads(_TOKEN_FILE.read_text(encoding="utf-8"))
            tok = data.get("access_token")
            # Tokens expire 3:30 AM IST next day; trust the saved date loosely.
            if tok:
                return tok
    except Exception:
        pass
    return None


def is_configured() -> bool:
    return access_token() is not None


def _headers() -> dict:
    return {"accept": "application/json", "Authorization": f"Bearer {access_token()}"}


def _get(path: str, params: dict) -> dict | None:
    try:
        with httpx.Client(timeout=10.0) as c:
            r = c.get(f"{_BASE}{path}", params=params, headers=_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


def _nearest_expiry(instrument_key: str) -> str | None:
    """Pick the nearest non-past expiry from the option-contract list."""
    ckey = f"expiry:{instrument_key}"
    hit = _cache.get(ckey)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    data = _get("/option/contract", {"instrument_key": instrument_key})
    if not data or data.get("status") != "success":
        return None
    today = date.today().isoformat()
    expiries = sorted({row.get("expiry") for row in data.get("data", []) if row.get("expiry")})
    future = [e for e in expiries if e >= today]
    exp = future[0] if future else (expiries[-1] if expiries else None)
    if exp:
        _cache[ckey] = (time.time(), exp)
    return exp


def get_option_chain(symbol: str) -> list[dict] | None:
    """Return rows in the app's option-chain format, or None if unavailable."""
    key = INSTRUMENT_KEYS.get(symbol.upper())
    if not key or not is_configured():
        return None

    expiry = _nearest_expiry(key)
    if not expiry:
        return None

    data = _get("/option/chain", {"instrument_key": key, "expiry_date": expiry})
    if not data or data.get("status") != "success":
        return None

    rows = []
    for item in data.get("data", []):
        ce = (item.get("call_options") or {}).get("market_data") or {}
        pe = (item.get("put_options") or {}).get("market_data") or {}
        rows.append({
            "strike": int(item.get("strike_price", 0)),
            "ce_oi": int(ce.get("oi") or 0),
            "ce_chg_oi": int((ce.get("oi") or 0) - (ce.get("prev_oi") or 0)),
            "ce_ltp": float(ce.get("ltp") or 0),
            "pe_oi": int(pe.get("oi") or 0),
            "pe_chg_oi": int((pe.get("oi") or 0) - (pe.get("prev_oi") or 0)),
            "pe_ltp": float(pe.get("ltp") or 0),
        })
    return rows or None
