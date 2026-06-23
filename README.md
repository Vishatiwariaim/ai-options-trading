# AI Options Trading Platform (NSE/BSE)

An AI-powered options trading **analytics & paper-trading** platform for Indian markets
(NIFTY, BANKNIFTY, FINNIFTY, SENSEX + stocks). It analyzes live/historical market data and
generates probabilistic BUY / SELL / CALL (CE) / PUT (PE) / EXIT signals with confidence
scores, risk-managed entries, and portfolio analytics.

> ⚠️ **Risk Disclaimer:** All signals are **probabilistic, not guaranteed financial advice**.
> No claim of profit or 90–100% accuracy is made. Trading involves substantial risk of loss.
> **Paper trading is the default mode.** Use real capital at your own risk.

---

## Architecture

```
trading-soft/
├── backend/        FastAPI + SQLAlchemy + JWT auth + WebSocket
│   ├── app/
│   │   ├── api/        REST routers (auth, market, option-chain, signals, risk, paper, portfolio, prediction)
│   │   ├── core/       config, security
│   │   ├── db/         SQLAlchemy models + session
│   │   ├── schemas/    Pydantic request/response models
│   │   └── services/   market data, indicators, option-chain analytics, signal engine, risk, ML
│   └── ml/         training pipeline (XGBoost / RandomForest / LSTM)
├── frontend/       Next.js 14 (App Router) + TypeScript + Tailwind
└── docker-compose.yml
```

### Tech stack
- **Frontend:** Next.js 14, React 18, TypeScript, Tailwind, lightweight-charts
- **Backend:** Python FastAPI, SQLAlchemy, Pydantic, WebSocket
- **DB / cache:** PostgreSQL (SQLite fallback for dev), Redis (optional)
- **Data:** yfinance + NSE public option-chain endpoints (free)
- **AI:** scikit-learn (RandomForest), XGBoost, TensorFlow/Keras (LSTM), ensemble

---

## Quick start (dev)

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy ..\.env.example .env       # then edit
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:3000

### 3. (Optional) Train ML models
```bash
cd backend
python -m ml.train --symbol ^NSEI --models all
```
Saves models to `backend/ml/artifacts/`. The prediction API auto-loads them; until trained,
it falls back to the rule-based signal engine.

### Docker
```bash
docker-compose up --build
```

---

## Modules implemented (MVP)
- ✅ User auth (register / login / JWT, role-based admin)
- ✅ Market data engine (indices + stocks, historical + snapshot)
- ✅ Option-chain analyzer (OI, ΔOI, PCR, Max Pain, support/resistance)
- ✅ 4-layer weighted signal engine (indicators + price action + SMC + options analytics)
- ✅ AI prediction engine (XGBoost / RandomForest / LSTM ensemble, multi-horizon)
- ✅ Risk management (position sizing, SL, R:R, exposure)
- ✅ Paper trading (virtual capital, simulated fills, P&L)
- ✅ Portfolio dashboard (P&L, win rate, drawdown, risk score)
- ✅ Next.js dashboard UI with charts and signal cards

## Roadmap (stubbed / future-ready)
- KYC, subscriptions/billing, Google OAuth
- Telegram / WhatsApp / push alerts
- Backtesting engine UI
- News & sentiment AI
- Kubernetes/AWS production infra
```
```

## License
Educational use. Not investment advice.
