from fastapi import APIRouter
router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/health")
def reports_health():
    return {"message": "Reports module ready"}
