from fastapi import APIRouter
router = APIRouter(prefix="/optimization", tags=["optimization"])

@router.get("/capabilities")
def capabilities():
    return {"supported": ["grid_search", "walk_forward", "monte_carlo"]}
