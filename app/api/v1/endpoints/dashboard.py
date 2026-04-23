from fastapi import APIRouter
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def dashboard_summary():
    return {"message": "Dashboard summary endpoint ready"}
