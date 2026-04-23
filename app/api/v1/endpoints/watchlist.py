from fastapi import APIRouter
router = APIRouter(prefix="/watchlist", tags=["watchlist"])

@router.get("")
def watchlist():
    return {"items": []}
