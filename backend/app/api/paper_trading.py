from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User, PaperTrade
from app.db.session import get_db
from app.schemas.schemas import (
    PaperTradeCreate, PaperTradeClose, PaperTradeOut, PortfolioSummary,
)
from app.services import market_data

router = APIRouter(prefix="/api/paper", tags=["paper-trading"])


def _pnl(trade: PaperTrade, exit_price: float) -> float:
    direction = 1 if trade.side == "BUY" else -1
    return round((exit_price - trade.entry_price) * trade.quantity * direction, 2)


@router.post("/trades", response_model=PaperTradeOut, status_code=201)
def open_trade(payload: PaperTradeCreate, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    trade = PaperTrade(
        user_id=user.id, symbol=payload.symbol.upper(), instrument=payload.instrument,
        side=payload.side.upper(), quantity=payload.quantity, entry_price=payload.entry_price,
        stop_loss=payload.stop_loss, target=payload.target, note=payload.note, status="OPEN",
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/trades", response_model=list[PaperTradeOut])
def list_trades(status: str | None = None, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    q = db.query(PaperTrade).filter(PaperTrade.user_id == user.id)
    if status:
        q = q.filter(PaperTrade.status == status.upper())
    return q.order_by(PaperTrade.opened_at.desc()).all()


@router.post("/trades/{trade_id}/close", response_model=PaperTradeOut)
def close_trade(trade_id: int, payload: PaperTradeClose, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    trade = db.query(PaperTrade).filter(
        PaperTrade.id == trade_id, PaperTrade.user_id == user.id).first()
    if not trade:
        raise HTTPException(404, "Trade not found")
    if trade.status == "CLOSED":
        raise HTTPException(400, "Trade already closed")
    trade.exit_price = payload.exit_price
    trade.pnl = _pnl(trade, payload.exit_price)
    trade.status = "CLOSED"
    trade.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trade)
    return trade


def _mark_price(trade: PaperTrade) -> float:
    # We only have a live feed for the underlying, not option premiums. Marking a
    # CE/PE/FUT position against the index spot would be meaningless, so options/
    # futures are held at entry (0 unrealized) until the user closes them manually.
    if trade.instrument != "EQ":
        return trade.entry_price
    try:
        return market_data.get_quote(trade.symbol)["last_price"]
    except Exception:
        return trade.entry_price


@router.get("/portfolio", response_model=PortfolioSummary)
def portfolio(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    trades = db.query(PaperTrade).filter(PaperTrade.user_id == user.id).all()
    closed = [t for t in trades if t.status == "CLOSED"]
    open_trades = [t for t in trades if t.status == "OPEN"]

    realized = round(sum(t.pnl for t in closed), 2)
    invested = round(sum(t.entry_price * t.quantity for t in open_trades), 2)
    open_pnl = round(sum(_pnl(t, _mark_price(t)) for t in open_trades), 2)

    wins = [t for t in closed if t.pnl > 0]
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0

    # Max drawdown over realized equity curve
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for t in sorted(closed, key=lambda x: x.closed_at or x.opened_at):
        equity += t.pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)

    today = date.today()
    daily = round(sum(
        t.pnl for t in closed if t.closed_at and t.closed_at.date() == today), 2)

    total_pnl = round(realized + open_pnl, 2)
    # Simple risk score: blends exposure ratio and drawdown (0 best .. 100 worst)
    exposure_ratio = invested / user.capital if user.capital else 0
    risk_score = round(min(100, exposure_ratio * 60 + abs(max_dd) / max(user.capital, 1) * 100 * 40), 1)

    return PortfolioSummary(
        total_capital=round(user.capital + realized, 2),
        invested=invested,
        open_pnl=open_pnl,
        realized_pnl=realized,
        total_pnl=total_pnl,
        daily_pnl=daily,
        win_rate=win_rate,
        total_trades=len(trades),
        open_trades=len(open_trades),
        max_drawdown=round(max_dd, 2),
        risk_score=risk_score,
    )
