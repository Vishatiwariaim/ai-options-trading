"""Generate a static data.json for the GitHub-Pages live dashboard.

Run by GitHub Actions on a schedule: fetches live market data, computes the
best-deal signal + quotes, and writes the result to docs/data.json. The static
site reads that file — no live backend server needed.

Usage:  python -m scripts.generate_data        (run from the backend/ dir)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.services import signal_engine, market_data

# Repo root = two levels up from backend/scripts/
OUT = Path(__file__).resolve().parents[2] / "docs" / "data.json"


def build() -> dict:
    deal = signal_engine.best_deal()
    sym = deal.get("symbol")
    if sym:
        deal["candles"] = market_data.get_candles(sym, period="60d", interval="15m")

    quotes = []
    for s in market_data.SYMBOL_MAP:
        try:
            q = market_data.get_quote(s)
            quotes.append({
                "symbol": q["symbol"], "name": q["name"],
                "last_price": q["last_price"], "change": q["change"],
                "change_pct": q["change_pct"], "source": q["source"],
            })
        except Exception:
            continue

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": market_data.data_source(),
        "best_deal": deal,
        "quotes": quotes,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")
    bd = data["best_deal"]
    print(f"Wrote {OUT}")
    print(f"  source={data['data_source']} quotes={len(data['quotes'])}")
    print(f"  best_deal={bd.get('action')} {bd.get('symbol')} "
          f"win={bd.get('win_chance')}% quality={bd.get('quality')}")


if __name__ == "__main__":
    main()
