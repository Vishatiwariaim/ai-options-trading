from fastapi import APIRouter, Query

from app.services import market_data, option_chain

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/symbols")
def symbols():
    return market_data.list_symbols()


@router.get("/quote/{symbol}")
def quote(symbol: str):
    return market_data.get_quote(symbol)


@router.get("/candles/{symbol}")
def candles(symbol: str, period: str = Query("60d"), interval: str = Query("15m")):
    rows = market_data.get_candles(symbol, period, interval)
    return {
        "symbol": symbol.upper(),
        "source": market_data.data_source(symbol),
        "candles": rows,
    }


@router.get("/data-source")
def data_source():
    """LIVE if any tracked ticker is fetching real data, else DEMO (synthetic)."""
    return {"source": market_data.data_source()}


@router.get("/option-chain/{symbol}")
def chain(symbol: str):
    return option_chain.analyze(symbol)
