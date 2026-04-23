from fastapi import APIRouter
router = APIRouter(prefix="/risk", tags=["risk"])

@router.get("/rules")
def risk_rules():
    return {"max_positions": 5, "risk_per_trade_pct": 1.0}
