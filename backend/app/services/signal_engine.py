"""4-layer weighted signal engine.

Layer 1  Technical indicators  (RSI, MACD, VWAP, SuperTrend, EMA stack)   weight 30
Layer 2  Price action          (breakout, ORB, market structure)          weight 20
Layer 3  Smart Money Concepts  (BOS/CHoCH, order block, FVG proxy)        weight 20
Layer 4  Options analytics     (PCR, OI buildup, Max Pain)                weight 25
         Sentiment (placeholder neutral)                                  weight  5

Total score 0-100 -> STRONG_SELL .. STRONG_BUY. Also picks CE/PE instrument
and derives entry / targets / stop-loss from ATR.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from app.services import market_data, indicators, option_chain

DISCLAIMER = (
    "Probabilistic signal, NOT guaranteed financial advice. "
    "No profit or accuracy guarantee. Trade at your own risk. Paper trading recommended."
)


def _score_indicators(ind: dict) -> tuple[float, dict]:
    """Return 0-30."""
    score = 0.0
    detail = {}
    close = ind["close"]

    # RSI (max 7)
    rsi = ind["rsi"] or 50
    if rsi < 30:
        s = 7
    elif rsi < 45:
        s = 5
    elif rsi <= 55:
        s = 3.5
    elif rsi <= 70:
        s = 2
    else:
        s = 0.5
    detail["rsi"] = s
    score += s

    # MACD histogram (max 7)
    s = 7 if (ind["macd_hist"] or 0) > 0 else 1.5
    detail["macd"] = s
    score += s

    # VWAP (max 6)
    s = 6 if close and ind["vwap"] and close > ind["vwap"] else 1.5
    detail["vwap"] = s
    score += s

    # EMA stack 20>50>200 (max 6)
    e20, e50, e200 = ind["ema20"], ind["ema50"], ind["ema200"]
    if e20 and e50 and e200:
        if e20 > e50 > e200:
            s = 6
        elif e20 > e50:
            s = 4
        elif e20 < e50 < e200:
            s = 0.5
        else:
            s = 2.5
    else:
        s = 3
    detail["ema_stack"] = s
    score += s

    # SuperTrend (max 4)
    s = 4 if ind["supertrend"] == 1 else 0.5
    detail["supertrend"] = s
    score += s
    return round(score, 1), detail


def _score_price_action(df) -> tuple[float, dict]:
    """Return 0-20 from breakout / structure on the candle frame."""
    close = df["Close"]
    high20 = df["High"].rolling(20).max().iloc[-2]
    low20 = df["Low"].rolling(20).min().iloc[-2]
    last = close.iloc[-1]
    detail = {}
    score = 0.0

    # Breakout of 20-bar range (max 8)
    if last > high20:
        s = 8
    elif last < low20:
        s = 1
    else:
        s = 4
    detail["breakout"] = s
    score += s

    # Higher highs / higher lows market structure over last 10 bars (max 7)
    recent = close.tail(10)
    up = (recent.diff().dropna() > 0).sum()
    s = round(7 * (up / 9), 1)
    detail["market_structure"] = s
    score += s

    # Opening range proxy: close vs session midpoint (max 5)
    mid = (df["High"].tail(25).max() + df["Low"].tail(25).min()) / 2
    s = 5 if last > mid else 1.5
    detail["orb"] = s
    score += s
    return round(score, 1), detail


def _score_smc(df) -> tuple[float, dict]:
    """Smart Money Concepts proxy 0-20 (BOS/CHoCH + FVG)."""
    close = df["Close"]
    detail = {}
    score = 0.0

    # Break of Structure: last close breaks prior swing high (max 10)
    swing_high = df["High"].iloc[-12:-2].max()
    swing_low = df["Low"].iloc[-12:-2].min()
    last = close.iloc[-1]
    if last > swing_high:
        s, struct = 10, "BOS_UP"
    elif last < swing_low:
        s, struct = 2, "BOS_DOWN"
    else:
        s, struct = 5, "RANGE"
    detail["bos_choch"] = struct
    detail["bos_score"] = s
    score += s

    # Fair value gap proxy: bullish gap in last 3 bars (max 10)
    h, l = df["High"], df["Low"]
    fvg_bull = l.iloc[-1] > h.iloc[-3]
    fvg_bear = h.iloc[-1] < l.iloc[-3]
    s = 10 if fvg_bull else (2 if fvg_bear else 5)
    detail["fvg"] = s
    score += s
    return round(score, 1), detail


def _score_options(oc: dict) -> tuple[float, dict]:
    """Options analytics 0-25 from PCR + max-pain positioning."""
    detail = {}
    score = 0.0
    pcr = oc["pcr"]

    # PCR (max 13): high PCR = bullish (puts being written)
    if pcr >= 1.4:
        s = 13
    elif pcr >= 1.1:
        s = 10
    elif pcr >= 0.9:
        s = 7
    elif pcr >= 0.7:
        s = 4
    else:
        s = 1.5
    detail["pcr"] = s
    score += s

    # Spot vs Max Pain (max 12): spot below max pain -> upward pull
    spot, mp = oc["spot"], oc["max_pain"]
    if spot < mp * 0.997:
        s = 12
    elif spot > mp * 1.003:
        s = 4
    else:
        s = 8
    detail["max_pain"] = s
    score += s
    return round(score, 1), detail


def _resample(df, rule: str):
    """Aggregate an intraday frame to a higher timeframe (OHLCV)."""
    agg = df.resample(rule).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    return agg.dropna()


def _mtf_trend(df) -> str:
    """Higher-timeframe (1h) trend: UP / DOWN / FLAT. Built from the same series."""
    try:
        h1 = _resample(df, "1h")
        if len(h1) < 25:
            return "FLAT"
        c = float(h1["Close"].iloc[-1])
        e20 = float(indicators.ema(h1["Close"], 20).iloc[-1])
        e50 = float(indicators.ema(h1["Close"], 50).iloc[-1]) if len(h1) >= 50 else e20
        if c > e20 and e20 >= e50:
            return "UP"
        if c < e20 and e20 <= e50:
            return "DOWN"
        return "UP" if c > e20 else "DOWN" if c < e20 else "FLAT"
    except Exception:
        return "FLAT"


def _layer_votes(s1: float, s2: float, s3: float, s4: float) -> dict:
    """Per-layer directional vote (+1 bull / -1 bear / 0 neutral) around each midpoint."""
    return {
        "indicators": 1 if s1 > 16 else -1 if s1 < 13 else 0,   # /30
        "price_action": 1 if s2 > 11 else -1 if s2 < 8 else 0,  # /20
        "smc": 1 if s3 > 11 else -1 if s3 < 8 else 0,           # /20
        "options": 1 if s4 > 13 else -1 if s4 < 10 else 0,      # /25
    }


def _grade(adx_val: float, agree: int, aligned: bool, against: bool, ev: float) -> str:
    """A = high-conviction, B = ok, C = skip/weak."""
    if against or ev <= 0 or adx_val < 18:
        return "C"
    if aligned and agree >= 3 and adx_val >= 25 and ev >= 0.4:
        return "A"
    return "B"


def _classify(score: float) -> str:
    if score >= 80:
        return "STRONG_BUY"
    if score >= 60:
        return "BUY"
    if score >= 40:
        return "NEUTRAL"
    if score >= 20:
        return "SELL"
    return "STRONG_SELL"


def generate(symbol: str) -> dict:
    df = market_data.get_history(symbol, period="60d", interval="15m")
    ind = indicators.compute_all(df)
    oc = option_chain.analyze(symbol)

    s1, d1 = _score_indicators(ind)
    s2, d2 = _score_price_action(df)
    s3, d3 = _score_smc(df)
    s4, d4 = _score_options(oc)
    sentiment = 2.5  # neutral placeholder (News & Sentiment AI = roadmap)

    # Accuracy guard: only trust the options layer when the chain is REAL (NSE).
    # If it's synthetic, drop it and renormalise so the signal reflects only
    # real price-derived data instead of fabricated PCR/OI.
    oc_live = oc.get("source") in ("nse", "upstox")
    if oc_live:
        total = round(s1 + s2 + s3 + s4 + sentiment, 1)        # full /100
    else:
        total = round((s1 + s2 + s3 + sentiment) / 75 * 100, 1)  # real layers only, rescaled
    signal = _classify(total)

    bullish = signal in ("STRONG_BUY", "BUY")
    instrument = "CE" if bullish else "PE" if signal in ("STRONG_SELL", "SELL") else "EQ"

    spot = ind["close"] or oc["spot"]
    atr = ind["atr"] or spot * 0.01

    # Confidence: distance from neutral (50) scaled to 0-100, floored for readability
    confidence = round(min(95, 50 + abs(total - 50) * 0.9), 1)

    if bullish:
        entry = round(spot, 2)
        stop_loss = round(spot - 1.5 * atr, 2)
        target1 = round(spot + 2 * atr, 2)
        target2 = round(spot + 3.5 * atr, 2)
    elif instrument == "PE":
        entry = round(spot, 2)
        stop_loss = round(spot + 1.5 * atr, 2)
        target1 = round(spot - 2 * atr, 2)
        target2 = round(spot - 3.5 * atr, 2)
    else:
        entry = round(spot, 2)
        stop_loss = round(spot - 1.2 * atr, 2)
        target1 = round(spot + 1.5 * atr, 2)
        target2 = round(spot + 2.5 * atr, 2)

    risk = abs(entry - stop_loss) or 1
    reward = abs(target1 - entry)
    rr_mult = reward / risk
    rr = f"1 : {round(rr_mult, 1)}"

    # --- Algorithm v2: multi-timeframe + trend-strength + confluence + EV ---
    adx_val = ind.get("adx") or 0.0
    mtf = _mtf_trend(df)
    direction = "BULL" if total >= 50 else "BEAR"
    votes = _layer_votes(s1, s2, s3, s4)
    bull_votes = sum(1 for v in votes.values() if v > 0)
    bear_votes = sum(1 for v in votes.values() if v < 0)
    agree = bull_votes if direction == "BULL" else bear_votes

    aligned = (direction == "BULL" and mtf == "UP") or (direction == "BEAR" and mtf == "DOWN")
    against = (direction == "BULL" and mtf == "DOWN") or (direction == "BEAR" and mtf == "UP")

    # Calibrated win probability — compressed so we never overclaim certainty.
    p = 0.5 + (total - 50) / 100 * 0.7
    p += 0.05 if aligned else 0
    p -= 0.08 if against else 0
    p += 0.03 if adx_val >= 25 else (-0.05 if adx_val < 18 else 0)
    p += 0.02 * (agree - 2)  # reward broad agreement, penalise lone-layer calls
    p = max(0.30, min(0.85, p))
    win_probability = round(p * 100, 1)

    # Expected value in R multiples (risking 1R to make rr_mult R).
    expected_value = round(p * rr_mult - (1 - p) * 1.0, 2)
    quality = _grade(adx_val, agree, aligned, against, expected_value)

    return {
        "symbol": oc["symbol"],
        "signal": signal,
        "instrument": instrument,
        "confidence": confidence,
        "score": total,
        "win_probability": win_probability,
        "expected_value": expected_value,
        "quality": quality,
        "mtf_trend": mtf,
        "adx": round(float(adx_val), 1),
        "agreement": f"{agree}/4 layers {direction.lower()}",
        "entry": entry,
        "target1": target1,
        "target2": target2,
        "stop_loss": stop_loss,
        "risk_reward": rr,
        "breakdown": {
            "layer1_indicators": {"score": s1, "weight": 30, "detail": d1},
            "layer2_price_action": {"score": s2, "weight": 20, "detail": d2},
            "layer3_smc": {"score": s3, "weight": 20, "detail": d3},
            "layer4_options": {
                "score": s4, "weight": 25 if oc_live else 0,
                "used": oc_live,
                "detail": d4 if oc_live else "excluded — option chain is synthetic (NSE blocked)",
            },
            "sentiment": {"score": sentiment, "weight": 5, "detail": "neutral (roadmap)"},
            "indicators_snapshot": ind,
            "option_chain": {k: oc[k] for k in ("pcr", "max_pain", "bias", "support", "resistance", "source")},
        },
        "disclaimer": DISCLAIMER,
    }


def _reason(result: dict) -> str:
    """Short human-readable 'why' for the recommendation."""
    b = result["breakdown"]
    oc = b["option_chain"]
    ind = b["indicators_snapshot"]
    bits = [f"Options PCR {oc['pcr']} ({oc['bias'].lower()})"]
    struct = b["layer3_smc"]["detail"].get("bos_choch")
    if struct and struct != "RANGE":
        bits.append(f"structure {struct.replace('_', ' ')}")
    if ind.get("rsi") is not None:
        bits.append(f"RSI {round(ind['rsi'], 1)}")
    e20, e50 = ind.get("ema20"), ind.get("ema50")
    if e20 and e50:
        bits.append("EMA20>EMA50" if e20 > e50 else "EMA20<EMA50")
    return " · ".join(bits)


def best_deal() -> dict:
    """Agent: scan the universe and pick TODAY'S best risk-adjusted trade.

    v2 ranks by Expected Value (win% × reward − loss% × risk), confirmed by a
    higher-timeframe trend filter and a trend-strength (ADX) gate. If nothing
    clears the quality bar it returns WAIT. Probabilistic only — no guarantee.
    """
    candidates = []
    for sym in market_data.SYMBOL_MAP:
        try:
            candidates.append(generate(sym))
        except Exception:
            continue

    if not candidates:
        return {"action": "WAIT", "wait": True, "reason": "No data available.",
                "alternatives": [], "disclaimer": DISCLAIMER}

    directional = [c for c in candidates if c["instrument"] in ("CE", "PE")]
    # Best = highest expected value, tie-break on win probability.
    pool = directional or candidates
    pool.sort(key=lambda r: (r.get("expected_value", 0), r.get("win_probability", 0)), reverse=True)
    top = pool[0]

    # Quality gate: only recommend a high-conviction, positive-EV, non-C setup.
    tradeable = (
        top["instrument"] in ("CE", "PE")
        and top.get("expected_value", 0) > 0
        and top.get("quality") != "C"
    )
    if tradeable:
        action = "BUY CALL (CE)" if top["instrument"] == "CE" else "BUY PUT (PE)"
        wait = False
    else:
        action = "WAIT — no high-quality trade abhi"
        wait = True

    return {
        "as_of": datetime.now(timezone.utc),
        "action": action,
        "wait": wait,
        "symbol": top["symbol"],
        "instrument": top["instrument"],
        "signal": top["signal"],
        "win_chance": top.get("win_probability", top["confidence"]),
        "expected_value": top.get("expected_value"),
        "quality": top.get("quality"),
        "mtf_trend": top.get("mtf_trend"),
        "adx": top.get("adx"),
        "agreement": top.get("agreement"),
        "confidence": top["confidence"],
        "score": top["score"],
        "entry": top["entry"],
        "target1": top["target1"],
        "target2": top["target2"],
        "stop_loss": top["stop_loss"],
        "risk_reward": top["risk_reward"],
        "reason": _reason(top),
        "data_source": market_data.data_source(top["symbol"]),
        "data_quality": {
            "price": market_data.data_source(top["symbol"]),
            "option_chain": option_chain.option_chain_source(top["symbol"]),
            "delay": "~15 min delayed (free Yahoo data)",
        },
        "alternatives": [
            {"symbol": c["symbol"], "signal": c["signal"], "instrument": c["instrument"],
             "quality": c.get("quality"), "win_probability": c.get("win_probability"),
             "expected_value": c.get("expected_value")}
            for c in pool[1:4]
        ],
        "disclaimer": DISCLAIMER,
    }
