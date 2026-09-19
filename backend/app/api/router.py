from fastapi import APIRouter

from app.api.routes import analytics, events, health, profiles, reviews

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(events.router, prefix="/api", tags=["events"])
api_router.include_router(profiles.router, prefix="/api", tags=["profiles"])
api_router.include_router(reviews.router, prefix="/api", tags=["reviews"])
api_router.include_router(analytics.router, prefix="/api", tags=["analytics"])
