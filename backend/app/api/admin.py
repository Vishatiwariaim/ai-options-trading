from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import User, PaperTrade, SignalLog
from app.db.session import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [{
        "id": u.id, "email": u.email, "role": u.role, "plan": u.plan,
        "capital": u.capital, "created_at": u.created_at,
    } for u in db.query(User).all()]


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return {
        "total_users": db.query(User).count(),
        "total_trades": db.query(PaperTrade).count(),
        "total_signals": db.query(SignalLog).count(),
        "plans": {
            "free": db.query(User).filter(User.plan == "free").count(),
            "pro": db.query(User).filter(User.plan == "pro").count(),
            "elite": db.query(User).filter(User.plan == "elite").count(),
        },
    }
