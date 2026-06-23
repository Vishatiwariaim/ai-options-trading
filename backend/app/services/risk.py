"""Risk management: position sizing, stop loss, exposure."""
from __future__ import annotations


def calculate(capital: float, risk_pct: float, entry: float, stop_loss: float, lot_size: int = 1) -> dict:
    max_risk = capital * (risk_pct / 100.0)
    risk_per_unit = abs(entry - stop_loss)
    if risk_per_unit <= 0:
        risk_per_unit = max(entry * 0.01, 0.05)

    raw_qty = int(max_risk // risk_per_unit)
    lot_size = max(lot_size, 1)
    lots = max(raw_qty // lot_size, 0)
    qty = lots * lot_size if lot_size > 1 else raw_qty
    if qty == 0:  # at least flag it's too tight
        qty = 0
        lots = 0
    exposure = round(qty * entry, 2)

    note = (
        f"Risking {risk_pct}% (₹{round(max_risk)}) of ₹{round(capital)}. "
        f"Per-unit risk ₹{round(risk_per_unit, 2)}."
    )
    if exposure > capital:
        note += " ⚠️ Exposure exceeds capital — consider leverage/margin carefully."

    return {
        "capital": capital,
        "max_risk_amount": round(max_risk, 2),
        "risk_per_unit": round(risk_per_unit, 2),
        "suggested_quantity": qty,
        "suggested_lots": lots,
        "exposure": exposure,
        "risk_reward_note": note,
    }
