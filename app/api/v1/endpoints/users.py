from fastapi import APIRouter
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
def current_user():
    return {"username": "admin", "role": "admin"}
