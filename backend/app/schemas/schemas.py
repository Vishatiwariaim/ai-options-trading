from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    role: str
    plan: str
    capital: float
    is_verified: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Market ----------
class Quote(BaseModel):
    symbol: str
    name: str
    last_price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: float
    timestamp: datetime


class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


# ---------- Option chain ----------
class OptionChainAnalysis(BaseModel):
    symbol: str
    spot: float
    pcr: float
    max_pain: float
    support: List[float]
    resistance: List[float]
    total_ce_oi: float
    total_pe_oi: float
    bias: str
    rows: list


# ---------- Signal ----------
class SignalOut(BaseModel):
    symbol: str
    signal: str
    instrument: str
    confidence: float
    score: float
    entry: float
    target1: float
    target2: float
    stop_loss: float
    risk_reward: str
    breakdown: dict
    disclaimer: str


# ---------- Risk ----------
class RiskRequest(BaseModel):
    capital: float = 100000
    risk_pct: float = 1.0
    entry: float
    stop_loss: float
    lot_size: int = 1


class RiskResponse(BaseModel):
    capital: float
    max_risk_amount: float
    risk_per_unit: float
    suggested_quantity: int
    suggested_lots: int
    exposure: float
    risk_reward_note: str


# ---------- Paper trading ----------
class PaperTradeCreate(BaseModel):
    symbol: str
    instrument: str = "EQ"
    side: str = "BUY"
    quantity: int
    entry_price: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    note: Optional[str] = None


class PaperTradeClose(BaseModel):
    exit_price: float


class PaperTradeOut(BaseModel):
    id: int
    symbol: str
    instrument: str
    side: str
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    stop_loss: Optional[float]
    target: Optional[float]
    status: str
    pnl: float
    opened_at: datetime
    closed_at: Optional[datetime]
    note: Optional[str]

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_capital: float
    invested: float
    open_pnl: float
    realized_pnl: float
    total_pnl: float
    daily_pnl: float
    win_rate: float
    total_trades: int
    open_trades: int
    max_drawdown: float
    risk_score: float
