from fastapi import APIRouter
from app.config.settings import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("")
def app_settings():
    settings = get_settings()
    return {"app_name": settings.app_name, "env": settings.app_env, "debug": settings.debug}
