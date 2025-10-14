"""
Meal Entry API Endpoints.

This module provides REST API endpoints for meal tracking:
- POST /meal-entries/manual - Create meal entry with full nutrition data
- POST /meal-entries/from-food - Create from existing food in database
- POST /meal-entries/batch - Create multiple entries at once
- GET /meal-entries/{id} - Get single meal entry
- GET /meal-entries - List with filters and pagination
- GET /meal-entries/daily/{date} - Get complete day summary
- PUT /meal-entries/{id} - Update meal entry
- DELETE /meal-entries/{id} - Delete meal entry
"""

from datetime import date, datetime
from datetime import time as time_type
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.schemas.meal_entry import (
    MealEntryCreateManual,
    MealEntryCreateFromFood,
    MealEntryCreateBatch,
    MealEntryUpdate,
    MealEntryResponse,
    MealEntryListResponse,
    DailyMealSummary,
    MealTypeClassification
)
from app.services.meal_entry_service import MealEntryService, classify_meal_type_by_time


# =====================================================
# ROUTER SETUP
# =====================================================

router = APIRouter(prefix="/meal-entries", tags=["Meal Entries"])


# =====================================================
# DEPENDENCIES
# =====================================================

def get_supabase_client() -> Client:
    """Get Supabase client (placeholder - implement actual auth)."""
    # TODO: Implement actual Supabase client from environment
    from os import getenv
    from supabase import create_client
    return create_client(
        getenv("SUPABASE_URL", ""),
        getenv("SUPABASE_SERVICE_KEY", "")
    )


def get_current_user_id() -> UUID:
    """Get current authenticated user ID (placeholder)."""
    # TODO: Implement actual JWT validation
    return UUID("00000000-0000-0000-0000-000000000001")


def get_meal_entry_service(
    supabase: Client = Depends(get_supabase_client)
) -> MealEntryService:
    """Get meal entry service instance."""
    return MealEntryService(supabase)


# =====================================================
# CREATE ENDPOINTS
# =====================================================

@router.post("/manual", response_model=MealEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_entry_manual(
    entry: MealEntryCreateManual,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Create a meal entry manually with all nutrition data.

    Use this when user provides complete nutrition information,
    or when logging food not in the database.

    **Example:**
    ```json
    {
      "food_name": "Homemade chicken soup",
      "date": "2024-10-14",
      "time": "13:30:00",
      "meal_type": null,
      "quantity_g": 350,
      "calories": 180,
      "protein_g": 18,
      "carbs_g": 12,
      "fat_g": 6,
      "logged_via": "chat",
      "original_input": "I had a bowl of chicken soup for lunch"
    }
    ```

    **Automatic Classification:**
    - If `meal_type` is null, it will be auto-classified by time
    - Time ranges: breakfast (5-11am), lunch (11am-4pm), dinner (4-10pm), snack (other)

    **Validation:**
    - Calories must match macros within 5% tolerance: (P*4 + C*4 + F*9)
    - Date cannot be in the future
    - All nutrition values must be >= 0
    """
    try:
        result = await service.create_meal_entry_manual(
            user_id=user_id,
            food_name=entry.food_name,
            quantity_g=entry.quantity_g,
            calories=entry.calories,
            protein_g=entry.protein_g,
            carbs_g=entry.carbs_g,
            fat_g=entry.fat_g,
            meal_date=entry.meal_date,
            meal_time=entry.meal_time,
            meal_type=entry.meal_type,
            logged_via=entry.logged_via,
            original_input=entry.original_input
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/from-food", response_model=MealEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_entry_from_food(
    entry: MealEntryCreateFromFood,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Create a meal entry from an existing food in the database.

    Nutrition values are automatically calculated based on the quantity.
    Use this when user selects a food from search results.

    **Example:**
    ```json
    {
      "food_id": "123e4567-e89b-12d3-a456-426614174000",
      "quantity_g": 150,
      "date": "2024-10-14",
      "time": "08:30:00",
      "logged_via": "manual"
    }
    ```

    **Automatic Features:**
    - Nutrition calculated from food database (scaled to quantity)
    - Meal type auto-classified by time if not provided
    - Food name copied from database

    **Requirements:**
    - Either `food_id` (system food) OR `user_food_id` (custom food) must be provided
    - Cannot provide both
    - Food must exist in database
    """
    try:
        result = await service.create_meal_entry_from_food(
            user_id=user_id,
            food_id=entry.food_id,
            user_food_id=entry.user_food_id,
            quantity_g=entry.quantity_g,
            meal_date=entry.meal_date,
            meal_time=entry.meal_time,
            meal_type=entry.meal_type,
            logged_via=entry.logged_via,
            original_input=entry.original_input
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/batch", response_model=List[MealEntryResponse], status_code=status.HTTP_201_CREATED)
async def create_meal_entries_batch(
    batch: MealEntryCreateBatch,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Create multiple meal entries at once (for a complete meal).

    Useful when user logs a meal with multiple foods:
    "I had chicken, rice, and broccoli for lunch"

    **Example:**
    ```json
    {
      "entries": [
        {"food_id": "uuid-1", "quantity_g": 150},
        {"food_id": "uuid-2", "quantity_g": 200},
        {"user_food_id": "uuid-3", "quantity_g": 100}
      ],
      "meal_type": "lunch",
      "date": "2024-10-14",
      "time": "13:00:00",
      "original_input": "I had chicken, rice, and broccoli for lunch"
    }
    ```

    **Features:**
    - All entries get the same date, time, and meal_type
    - Each food's nutrition is calculated individually
    - Returns array of created entries
    - Limit: 1-50 foods per batch
    """
    try:
        results = []
        for item in batch.entries:
            result = await service.create_meal_entry_from_food(
                user_id=user_id,
                food_id=item.food_id,
                user_food_id=item.user_food_id,
                quantity_g=item.quantity_g,
                meal_date=batch.meal_date,
                meal_time=batch.meal_time,
                meal_type=batch.meal_type,
                logged_via=item.logged_via,
                original_input=batch.original_input
            )
            results.append(result)
        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =====================================================
# READ ENDPOINTS
# =====================================================

@router.get("/{entry_id}", response_model=MealEntryResponse)
async def get_meal_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Get a single meal entry by ID.

    Returns complete meal entry with all nutrition data.
    """
    result = await service.get_meal_entry(user_id, entry_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal entry not found: {entry_id}"
        )
    return result


@router.get("", response_model=MealEntryListResponse)
async def list_meal_entries(
    start_date: Optional[date] = Query(None, description="Start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date (inclusive)"),
    meal_type: Optional[str] = Query(None, description="Filter by meal type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    List meal entries with filters and pagination.

    **Filters:**
    - `start_date` / `end_date`: Date range (inclusive)
    - `meal_type`: breakfast, lunch, dinner, snack
    - `page` / `page_size`: Pagination

    **Example:**
    ```
    GET /meal-entries?start_date=2024-10-01&end_date=2024-10-14&meal_type=lunch&page=1&page_size=20
    ```

    **Response includes:**
    - `items`: Array of meal entries
    - `total`: Total count (for pagination)
    - `page`: Current page
    - `page_size`: Items per page
    - `has_more`: True if more pages available
    """
    try:
        entries, total = await service.list_meal_entries(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            meal_type=meal_type,
            page=page,
            page_size=page_size
        )

        return {
            "items": entries,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": total > (page * page_size)
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/daily/{target_date}", response_model=DailyMealSummary)
async def get_daily_meal_summary(
    target_date: date,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Get complete daily meal summary with nutrition totals.

    Returns all meals for the day grouped by meal type (breakfast, lunch, dinner, snacks)
    plus summary with total calories and macros.

    **Example:**
    ```
    GET /meal-entries/daily/2024-10-14
    ```

    **Response structure:**
    ```json
    {
      "date": "2024-10-14",
      "breakfast": [...meal entries...],
      "lunch": [...meal entries...],
      "dinner": [...meal entries...],
      "snacks": [...meal entries...],
      "summary": {
        "total_entries": 8,
        "total_calories": 1850,
        "total_protein_g": 120.5,
        "total_carbs_g": 180.2,
        "total_fat_g": 65.3,
        "protein_percent": 26.0,
        "carbs_percent": 38.9,
        "fat_percent": 31.8
      }
    }
    ```
    """
    try:
        result = await service.get_daily_meals(user_id, target_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =====================================================
# UPDATE/DELETE ENDPOINTS
# =====================================================

@router.put("/{entry_id}", response_model=MealEntryResponse)
async def update_meal_entry(
    entry_id: UUID,
    updates: MealEntryUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Update an existing meal entry.

    Can update any field. Nutrition values are re-validated if changed.

    **Example:**
    ```json
    {
      "quantity_g": 200,
      "calories": 300,
      "meal_type": "snack"
    }
    ```

    **Notes:**
    - Only provided fields are updated (partial update)
    - Nutrition validation applies if calories/macros changed
    - Cannot update to future date
    """
    try:
        # Convert to dict and remove None values
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

        if not update_data:
            raise ValueError("No fields to update")

        result = await service.update_meal_entry(user_id, entry_id, **update_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_entry(
    entry_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MealEntryService = Depends(get_meal_entry_service)
):
    """
    Delete a meal entry.

    **Confirmation required in UI before calling this endpoint.**

    Returns 204 No Content on success, 404 if not found.
    """
    try:
        deleted = await service.delete_meal_entry(user_id, entry_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meal entry not found: {entry_id}"
            )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =====================================================
# UTILITY ENDPOINTS
# =====================================================

@router.get("/classify-meal-type/{meal_time}", response_model=MealTypeClassification)
async def classify_meal_type(
    meal_time: str
):
    """
    Classify meal type based on time of day.

    Useful for UI to show suggested meal type before user confirms.

    **Example:**
    ```
    GET /meal-entries/classify-meal-type/13:30
    ```

    **Response:**
    ```json
    {
      "meal_type": "lunch",
      "confidence": 0.95,
      "reason": "Typical lunch time (13:30)"
    }
    ```

    **Time ranges:**
    - Breakfast: 05:00 - 10:59
    - Lunch: 11:00 - 15:59
    - Dinner: 16:00 - 21:59
    - Snack: 22:00 - 04:59
    """
    try:
        # Parse time
        time_obj = datetime.strptime(meal_time, "%H:%M").time()

        # Classify
        meal_type, confidence, reason = classify_meal_type_by_time(time_obj)

        return {
            "meal_type": meal_type,
            "confidence": confidence,
            "reason": reason
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time format. Use HH:MM (24-hour). Error: {str(e)}"
        )
