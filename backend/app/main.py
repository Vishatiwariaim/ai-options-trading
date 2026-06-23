import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.net import enable_os_trust_store
from app.db.session import init_db
from app.api import auth, market, signals, risk, paper_trading, admin

# Trust the OS cert store so HTTPS works behind corporate SSL-inspection proxies.
enable_os_trust_store()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered options trading analytics & paper-trading platform for NSE/BSE. "
                "Signals are probabilistic, NOT financial advice.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "disclaimer": "Probabilistic signals only. Not financial advice. Paper trading is default.",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


app.include_router(auth.router)
app.include_router(market.router)
app.include_router(signals.router)
app.include_router(risk.router)
app.include_router(paper_trading.router)
app.include_router(admin.router)


@app.websocket("/ws/quotes/{symbol}")
async def ws_quotes(websocket: WebSocket, symbol: str):
    """Realtime price feed (polls the data layer every few seconds)."""
    from app.services import market_data

    await websocket.accept()
    try:
        while True:
            quote = market_data.get_quote(symbol)
            await websocket.send_text(json.dumps(quote, default=str))
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close()
