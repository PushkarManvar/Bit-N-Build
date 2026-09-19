from fastapi import APIRouter

from app.api.routes import events, health, profiles

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(events.router, prefix="/api", tags=["events"])
api_router.include_router(profiles.router, prefix="/api", tags=["profiles"])
