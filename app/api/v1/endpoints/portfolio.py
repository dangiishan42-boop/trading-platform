from fastapi import APIRouter
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/summary")
def portfolio_summary():
    return {"message": "Portfolio module ready"}
