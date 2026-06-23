from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # user | admin
    is_verified = Column(Boolean, default=False)
    plan = Column(String, default="free")  # free | pro | elite
    capital = Column(Float, default=100000.0)  # default virtual capital
    created_at = Column(DateTime, default=_now)

    trades = relationship("PaperTrade", back_populates="user", cascade="all, delete-orphan")


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    instrument = Column(String, default="EQ")  # EQ | CE | PE | FUT
    side = Column(String, nullable=False)      # BUY | SELL
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    status = Column(String, default="OPEN")    # OPEN | CLOSED
    pnl = Column(Float, default=0.0)
    opened_at = Column(DateTime, default=_now)
    closed_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    user = relationship("User", back_populates="trades")


class SignalLog(Base):
    __tablename__ = "signal_logs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    signal = Column(String, nullable=False)       # STRONG_BUY etc.
    instrument = Column(String, nullable=True)     # CE | PE | EQ
    confidence = Column(Float, nullable=False)
    entry = Column(Float, nullable=True)
    target1 = Column(Float, nullable=True)
    target2 = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)
