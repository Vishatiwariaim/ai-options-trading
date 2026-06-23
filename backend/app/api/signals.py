from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import SignalLog
from app.services import signal_engine, ml_predict, market_data

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/best-deal")
def best_deal(db: Session = Depends(get_db)):
    """Agent: today's single best trade (CALL/PUT) + win-chance % + chart candles."""
    deal = signal_engine.best_deal()
    sym = deal.get("symbol")
    if sym:
        # Same 60d/15m series the signal was computed on (cached) → chart and
        # entry/SL/targets always agree, live or synthetic.
        deal["candles"] = market_data.get_candles(sym, period="60d", interval="15m")
        # Persist the pick for history/audit.
        if deal.get("instrument") in ("CE", "PE", "EQ"):
            db.add(SignalLog(
                symbol=sym, signal=deal["signal"], instrument=deal["instrument"],
                confidence=deal["confidence"], entry=deal["entry"], target1=deal["target1"],
                target2=deal["target2"], stop_loss=deal["stop_loss"], score=deal["score"],
            ))
            db.commit()
    return deal


@router.get("/{symbol}")
def get_signal(symbol: str, db: Session = Depends(get_db)):
    result = signal_engine.generate(symbol)
    db.add(SignalLog(
        symbol=result["symbol"], signal=result["signal"], instrument=result["instrument"],
        confidence=result["confidence"], entry=result["entry"], target1=result["target1"],
        target2=result["target2"], stop_loss=result["stop_loss"], score=result["score"],
    ))
    db.commit()
    return result


@router.get("/{symbol}/prediction")
def get_prediction(symbol: str):
    return ml_predict.predict(symbol)


@router.get("")
def scan(db: Session = Depends(get_db)):
    """Quick scan across the tracked index/symbol universe."""
    from app.services.market_data import SYMBOL_MAP

    out = []
    for sym in SYMBOL_MAP:
        try:
            r = signal_engine.generate(sym)
            out.append({k: r[k] for k in ("symbol", "signal", "instrument", "confidence", "score",
                                          "entry", "target1", "stop_loss", "risk_reward")})
        except Exception as e:  # keep scan resilient
            out.append({"symbol": sym, "error": str(e)})
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"results": out, "disclaimer": signal_engine.DISCLAIMER}
