from fastapi import APIRouter

from app.schemas.schemas import RiskRequest, RiskResponse
from app.services import risk as risk_service

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/position-size", response_model=RiskResponse)
def position_size(req: RiskRequest):
    return risk_service.calculate(
        capital=req.capital, risk_pct=req.risk_pct, entry=req.entry,
        stop_loss=req.stop_loss, lot_size=req.lot_size,
    )
