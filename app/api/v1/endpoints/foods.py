"""
Food management endpoints.

Handles food search, CRUD operations for system and user foods,
favorites, and brands.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.schemas.food import (
    FoodSearchRequest,
    FoodSearchResponse,
    FoodSearchResultItem,
    FoodSearchFilters,
    FoodResponse,
    UserFoodCreate,
    UserFoodResponse,
    FoodFavoriteCreate,
    FoodFavoriteResponse,
)
from app.services.food_service import FoodSearchService
from app.core.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get current user ID from Supabase session
async def get_current_user_id() -> str:
    """
    Get current authenticated user ID.

    In production, this would extract user_id from JWT token.
    For now, using a placeholder for testing.

    TODO: Implement proper auth middleware with Supabase JWT validation
    """
    # Placeholder - in production, extract from Authorization header
    # Example: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    return "00000000-0000-0000-0000-000000000000"  # Replace with real user_id


@router.get("/search", response_model=FoodSearchResponse)
async def search_foods(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand_id: Optional[str] = Query(None, description="Filter by brand UUID"),
    only_user_foods: bool = Query(False, description="Only user's custom foods"),
    min_calories: Optional[float] = Query(None, ge=0, description="Minimum calories"),
    max_calories: Optional[float] = Query(None, ge=0, description="Maximum calories"),
    is_vegetarian: Optional[bool] = Query(None, description="Filter vegetarian"),
    is_vegan: Optional[bool] = Query(None, description="Filter vegan"),
    is_gluten_free: Optional[bool] = Query(None, description="Filter gluten-free"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Search for foods with intelligent prioritization.

    **Priority order:**
    1. User's custom foods (exact match)
    2. User's favorite foods
    3. System foods (exact match)
    4. Partial matches (user foods)
    5. Partial matches (system foods)
    6. Category matches

    **Filters:**
    - `category`: protein, grain, vegetable, fruit, dairy, snack
    - `brand_id`: Filter by specific brand
    - `only_user_foods`: Only return user's custom foods
    - `min_calories` / `max_calories`: Calorie range
    - `is_vegetarian` / `is_vegan` / `is_gluten_free`: Dietary filters

    **Example queries:**
    - `q=pollo` → Returns chicken-related foods
    - `q=manzana&category=fruit` → Returns apples in fruit category
    - `q=taco&max_calories=300` → Tacos under 300 calories
    """
    try:
        # Build filters
        filters = FoodSearchFilters(
            category=category,
            brand_id=brand_id,
            only_user_foods=only_user_foods,
            min_calories=min_calories,
            max_calories=max_calories,
            is_vegetarian=is_vegetarian,
            is_vegan=is_vegan,
            is_gluten_free=is_gluten_free,
        )

        # Search
        service = FoodSearchService()
        results, total_count = await service.search_foods(
            user_id=user_id,
            query=q,
            page=page,
            page_size=page_size,
            filters=filters,
        )

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        has_more = page < total_pages

        # Convert to Pydantic models
        result_items = [FoodSearchResultItem(**item) for item in results]

        return FoodSearchResponse(
            success=True,
            data=result_items,
            pagination={
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_more": has_more,
            },
            message=f"Found {total_count} results for '{q}'",
        )

    except Exception as e:
        logger.error(f"Food search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Food search failed", "error": str(e)},
        )


@router.get("/{food_id}", response_model=dict)
async def get_food_by_id(
    food_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get food details by ID.

    Searches in both system foods and user's custom foods.
    """
    try:
        service = FoodSearchService()
        food = await service.get_food_by_id(food_id, user_id)

        if not food:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Food not found", "food_id": food_id},
            )

        return {
            "success": True,
            "data": food,
            "message": "Food retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get food error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get food", "error": str(e)},
        )


@router.post("/user-foods", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user_food(
    food: UserFoodCreate,
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a custom user food.

    The food name must be unique per user. Calories are validated
    to match macro calculation within 10% tolerance.
    """
    try:
        supabase = get_supabase_client()

        # Check for duplicate name
        existing = (
            supabase.table("user_foods")
            .select("id")
            .eq("user_id", user_id)
            .eq("name", food.name)
            .maybe_single()
            .execute()
        )

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": f"You already have a food named '{food.name}'",
                    "field": "name",
                },
            )

        # Insert food
        food_data = food.dict()
        food_data["user_id"] = user_id

        response = supabase.table("user_foods").insert(food_data).execute()

        return {
            "success": True,
            "data": response.data[0],
            "message": f"Custom food '{food.name}' created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user food error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create custom food", "error": str(e)},
        )


@router.delete("/user-foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_food(
    food_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a custom user food.

    Only the owner can delete their custom foods.
    """
    try:
        supabase = get_supabase_client()

        # Verify ownership
        food = (
            supabase.table("user_foods")
            .select("id")
            .eq("id", food_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not food.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Custom food not found or access denied"},
            )

        # Delete
        supabase.table("user_foods").delete().eq("id", food_id).eq(
            "user_id", user_id
        ).execute()

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user food error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to delete custom food", "error": str(e)},
        )


@router.post("/favorites", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
    favorite: FoodFavoriteCreate,
    user_id: str = Depends(get_current_user_id),
):
    """
    Add a food to user's favorites.

    Either `food_id` (system food) or `user_food_id` (custom food) must be provided.
    """
    try:
        supabase = get_supabase_client()

        # Check if already favorited
        query = supabase.table("food_favorites").select("id").eq("user_id", user_id)

        if favorite.food_id:
            query = query.eq("food_id", favorite.food_id)
        else:
            query = query.eq("user_food_id", favorite.user_food_id)

        existing = query.maybe_single().execute()

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Food is already in favorites"},
            )

        # Insert favorite
        favorite_data = {
            "user_id": user_id,
            "food_id": favorite.food_id,
            "user_food_id": favorite.user_food_id,
            "use_count": 0,
        }

        response = supabase.table("food_favorites").insert(favorite_data).execute()

        return {
            "success": True,
            "data": response.data[0],
            "message": "Food added to favorites",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add favorite error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to add favorite", "error": str(e)},
        )


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    favorite_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Remove a food from user's favorites.
    """
    try:
        supabase = get_supabase_client()

        # Verify ownership and delete
        supabase.table("food_favorites").delete().eq("id", favorite_id).eq(
            "user_id", user_id
        ).execute()

        return None

    except Exception as e:
        logger.error(f"Remove favorite error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to remove favorite", "error": str(e)},
        )


@router.get("/favorites/frequent", response_model=dict)
async def get_frequent_foods(
    limit: int = Query(10, ge=1, le=50, description="Max number of results"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get user's most frequently used foods from favorites.

    Returns foods sorted by use_count descending.
    """
    try:
        supabase = get_supabase_client()

        # Call database function
        response = supabase.rpc(
            "get_user_frequent_foods", {"user_uuid": user_id, "limit_count": limit}
        ).execute()

        return {
            "success": True,
            "data": response.data,
            "message": f"Retrieved {len(response.data)} frequent foods",
        }

    except Exception as e:
        logger.error(f"Get frequent foods error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get frequent foods", "error": str(e)},
        )
