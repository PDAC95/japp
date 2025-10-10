"""
API v1 Router

Aggregates all v1 endpoints into a single router.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import chat, personalities

api_router = APIRouter()

# Include chat endpoints
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"]
)

# Include personalities endpoints
api_router.include_router(
    personalities.router,
    prefix="/personalities",
    tags=["Personalities"]
)

# Future endpoints will be added here:
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(food.router, prefix="/food", tags=["Food Tracking"])
# api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
# api_router.include_router(fasting.router, prefix="/fasting", tags=["Fasting"])
