from fastapi import APIRouter
router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/ping")
def ping_auth():
    return {"status": "auth module ready"}
