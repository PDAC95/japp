"""
API v1 Router

Aggregates all v1 endpoints into a single router.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import chat, personalities, foods, meal_entries, daily_summary

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

# Include foods endpoints
api_router.include_router(
    foods.router,
    prefix="/foods",
    tags=["Foods"]
)

# Include meal entries endpoints
api_router.include_router(
    meal_entries.router,
    tags=["Meal Entries"]
)

# Include daily summary endpoints
api_router.include_router(
    daily_summary.router,
    tags=["Daily Summary"]
)

# Future endpoints will be added here:
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
# api_router.include_router(fasting.router, prefix="/fasting", tags=["Fasting"])
