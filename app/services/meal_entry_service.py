"""
Meal Entry Service - Business logic for meal tracking.

This service handles:
- Creating meal entries (manual or from food database)
- Automatic meal type classification based on time
- Nutrition calculation and validation
- Daily/weekly summaries
- Integration with food database and macro service
"""

from datetime import date, datetime, timedelta
from datetime import time as time_type
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from supabase import Client

from app.services.macro_service import (
    calculate_calories_from_macros,
    validate_calorie_calculation,
    MacroCalculationService
)


# =====================================================
# MEAL TYPE CLASSIFICATION
# =====================================================

def classify_meal_type_by_time(meal_time: time_type) -> Tuple[str, float, str]:
    """
    Automatically classify meal type based on time of day.

    Time ranges (24-hour format):
    - Breakfast: 05:00 - 10:59
    - Lunch: 11:00 - 15:59
    - Dinner: 16:00 - 21:59
    - Snack: 22:00 - 04:59

    Args:
        meal_time: Time of the meal

    Returns:
        Tuple of (meal_type, confidence, reason)
    """
    hour = meal_time.hour

    # Core time ranges with high confidence
    if 7 <= hour <= 10:
        return ("breakfast", 0.95, f"Typical breakfast time ({meal_time.strftime('%H:%M')})")
    elif 12 <= hour <= 14:
        return ("lunch", 0.95, f"Typical lunch time ({meal_time.strftime('%H:%M')})")
    elif 18 <= hour <= 20:
        return ("dinner", 0.95, f"Typical dinner time ({meal_time.strftime('%H:%M')})")

    # Extended ranges with medium confidence
    elif 5 <= hour < 7:
        return ("breakfast", 0.75, f"Early breakfast ({meal_time.strftime('%H:%M')})")
    elif 11 <= hour < 12:
        return ("lunch", 0.75, f"Early lunch ({meal_time.strftime('%H:%M')})")
    elif 15 <= hour < 16:
        return ("lunch", 0.70, f"Late lunch ({meal_time.strftime('%H:%M')})")
    elif 16 <= hour < 18:
        return ("dinner", 0.70, f"Early dinner ({meal_time.strftime('%H:%M')})")
    elif 21 <= hour < 22:
        return ("dinner", 0.70, f"Late dinner ({meal_time.strftime('%H:%M')})")

    # Everything else is a snack
    else:
        return ("snack", 0.90, f"Outside main meal times ({meal_time.strftime('%H:%M')})")


def validate_meal_date(meal_date: date) -> Tuple[bool, str]:
    """
    Validate that meal date is not in the future.

    Args:
        meal_date: Date to validate

    Returns:
        Tuple of (is_valid, message)
    """
    today = date.today()

    if meal_date > today:
        return (False, f"Cannot log meals in the future. Date provided: {meal_date}, Today: {today}")

    # Warn if date is too far in the past (more than 30 days)
    days_ago = (today - meal_date).days
    if days_ago > 30:
        return (True, f"Warning: Logging meal from {days_ago} days ago")

    return (True, "Date is valid")


# =====================================================
# MEAL ENTRY SERVICE
# =====================================================

class MealEntryService:
    """Service for managing meal entries."""

    def __init__(self, supabase_client: Client):
        """
        Initialize meal entry service.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.macro_service = MacroCalculationService()

    # =====================================================
    # CREATE MEAL ENTRIES
    # =====================================================

    async def create_meal_entry_manual(
        self,
        user_id: UUID,
        food_name: str,
        quantity_g: Decimal,
        calories: int,
        protein_g: Decimal,
        carbs_g: Decimal,
        fat_g: Decimal,
        meal_date: date = None,
        meal_time: time_type = None,
        meal_type: str = None,
        logged_via: str = "manual",
        original_input: str = None
    ) -> Dict[str, Any]:
        """
        Create meal entry manually with all nutrition data.

        Args:
            user_id: User ID
            food_name: Name of the food
            quantity_g: Quantity in grams
            calories: Total calories
            protein_g: Protein in grams
            carbs_g: Carbs in grams
            fat_g: Fat in grams
            meal_date: Date (defaults to today)
            meal_time: Time (defaults to now)
            meal_type: Type (auto-classified if not provided)
            logged_via: How it was logged
            original_input: Original user input

        Returns:
            Created meal entry

        Raises:
            ValueError: If validation fails
        """
        # Default values
        if meal_date is None:
            meal_date = date.today()
        if meal_time is None:
            meal_time = datetime.now().time()

        # Validate date
        is_valid, message = validate_meal_date(meal_date)
        if not is_valid:
            raise ValueError(message)

        # Auto-classify meal type if not provided
        if meal_type is None:
            meal_type, confidence, reason = classify_meal_type_by_time(meal_time)

        # Validate nutrition
        is_valid, discrepancy, msg = validate_calorie_calculation(
            float(calories), float(protein_g), float(carbs_g), float(fat_g)
        )
        if not is_valid:
            raise ValueError(f"Calorie validation failed: {msg}")

        # Insert into database
        entry_data = {
            "user_id": str(user_id),
            "food_name": food_name,
            "date": str(meal_date),
            "time": meal_time.strftime("%H:%M:%S"),
            "meal_type": meal_type,
            "quantity_g": float(quantity_g),
            "calories": calories,
            "protein_g": float(protein_g),
            "carbs_g": float(carbs_g),
            "fat_g": float(fat_g),
            "logged_via": logged_via,
            "original_input": original_input
        }

        response = self.supabase.table("meal_entries").insert(entry_data).execute()

        return response.data[0] if response.data else None

    async def create_meal_entry_from_food(
        self,
        user_id: UUID,
        food_id: UUID = None,
        user_food_id: UUID = None,
        quantity_g: Decimal = 100,
        meal_date: date = None,
        meal_time: time_type = None,
        meal_type: str = None,
        logged_via: str = "manual",
        original_input: str = None
    ) -> Dict[str, Any]:
        """
        Create meal entry from existing food in database.
        Automatically calculates nutrition based on quantity.

        Args:
            user_id: User ID
            food_id: System food ID (exclusive with user_food_id)
            user_food_id: User custom food ID (exclusive with food_id)
            quantity_g: Quantity in grams (default 100g)
            meal_date: Date (defaults to today)
            meal_time: Time (defaults to now)
            meal_type: Type (auto-classified if not provided)
            logged_via: How it was logged
            original_input: Original user input

        Returns:
            Created meal entry

        Raises:
            ValueError: If validation fails or food not found
        """
        # Validate food reference
        if not food_id and not user_food_id:
            raise ValueError("Either food_id or user_food_id must be provided")
        if food_id and user_food_id:
            raise ValueError("Cannot provide both food_id and user_food_id")

        # Default values
        if meal_date is None:
            meal_date = date.today()
        if meal_time is None:
            meal_time = datetime.now().time()

        # Validate date
        is_valid, message = validate_meal_date(meal_date)
        if not is_valid:
            raise ValueError(message)

        # Fetch food data from database
        if food_id:
            response = self.supabase.table("foods").select("*").eq("id", str(food_id)).execute()
            if not response.data:
                raise ValueError(f"Food not found: {food_id}")
            food = response.data[0]
        else:
            response = self.supabase.table("user_foods").select("*").eq("id", str(user_food_id)).execute()
            if not response.data:
                raise ValueError(f"User food not found: {user_food_id}")
            food = response.data[0]

        # Calculate nutrition for quantity
        nutrition = self.macro_service.calculate_food_nutrition_for_quantity(
            food=food,
            quantity=float(quantity_g),
            unit="g"
        )

        # Auto-classify meal type if not provided
        if meal_type is None:
            meal_type, confidence, reason = classify_meal_type_by_time(meal_time)

        # Insert into database
        entry_data = {
            "user_id": str(user_id),
            "food_id": str(food_id) if food_id else None,
            "user_food_id": str(user_food_id) if user_food_id else None,
            "food_name": food["name"],
            "date": str(meal_date),
            "time": meal_time.strftime("%H:%M:%S"),
            "meal_type": meal_type,
            "quantity_g": float(quantity_g),
            "calories": int(nutrition["calories"]),
            "protein_g": nutrition["protein_g"],
            "carbs_g": nutrition["carbs_g"],
            "fat_g": nutrition["fat_g"],
            "logged_via": logged_via,
            "original_input": original_input
        }

        response = self.supabase.table("meal_entries").insert(entry_data).execute()

        return response.data[0] if response.data else None

    # =====================================================
    # READ MEAL ENTRIES
    # =====================================================

    async def get_meal_entry(
        self,
        user_id: UUID,
        entry_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single meal entry by ID.

        Args:
            user_id: User ID
            entry_id: Meal entry ID

        Returns:
            Meal entry or None if not found
        """
        response = self.supabase.table("meal_entries")\
            .select("*")\
            .eq("id", str(entry_id))\
            .eq("user_id", str(user_id))\
            .execute()

        return response.data[0] if response.data else None

    async def get_daily_meals(
        self,
        user_id: UUID,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Get all meals for a specific day grouped by meal type.

        Args:
            user_id: User ID
            target_date: Date to query

        Returns:
            Daily summary with meals grouped by type
        """
        # Fetch all entries for the day
        response = self.supabase.table("meal_entries")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .eq("date", str(target_date))\
            .order("time")\
            .execute()

        entries = response.data or []

        # Group by meal type
        breakfast = [e for e in entries if e.get("meal_type") == "breakfast"]
        lunch = [e for e in entries if e.get("meal_type") == "lunch"]
        dinner = [e for e in entries if e.get("meal_type") == "dinner"]
        snacks = [e for e in entries if e.get("meal_type") == "snack"]

        # Calculate summary
        summary = self._calculate_summary(entries)

        return {
            "date": target_date,
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "snacks": snacks,
            "summary": summary
        }

    async def list_meal_entries(
        self,
        user_id: UUID,
        start_date: date = None,
        end_date: date = None,
        meal_type: str = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List meal entries with filters and pagination.

        Args:
            user_id: User ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            meal_type: Filter by meal type
            page: Page number (starts at 1)
            page_size: Items per page

        Returns:
            Tuple of (entries, total_count)
        """
        query = self.supabase.table("meal_entries").select("*", count="exact").eq("user_id", str(user_id))

        # Apply filters
        if start_date:
            query = query.gte("date", str(start_date))
        if end_date:
            query = query.lte("date", str(end_date))
        if meal_type:
            query = query.eq("meal_type", meal_type)

        # Pagination
        offset = (page - 1) * page_size
        query = query.order("date", desc=True).order("time", desc=True).range(offset, offset + page_size - 1)

        response = query.execute()

        return (response.data or [], response.count or 0)

    # =====================================================
    # UPDATE/DELETE MEAL ENTRIES
    # =====================================================

    async def update_meal_entry(
        self,
        user_id: UUID,
        entry_id: UUID,
        **updates
    ) -> Dict[str, Any]:
        """
        Update an existing meal entry.

        Args:
            user_id: User ID
            entry_id: Meal entry ID
            **updates: Fields to update

        Returns:
            Updated meal entry

        Raises:
            ValueError: If entry not found or validation fails
        """
        # Check entry exists and belongs to user
        existing = await self.get_meal_entry(user_id, entry_id)
        if not existing:
            raise ValueError(f"Meal entry not found: {entry_id}")

        # If nutrition is being updated, validate
        if any(k in updates for k in ["calories", "protein_g", "carbs_g", "fat_g"]):
            calories = updates.get("calories", existing["calories"])
            protein = updates.get("protein_g", existing["protein_g"])
            carbs = updates.get("carbs_g", existing["carbs_g"])
            fat = updates.get("fat_g", existing["fat_g"])

            is_valid, discrepancy, msg = validate_calorie_calculation(
                float(calories), float(protein), float(carbs), float(fat)
            )
            if not is_valid:
                raise ValueError(f"Calorie validation failed: {msg}")

        # Update in database
        response = self.supabase.table("meal_entries")\
            .update(updates)\
            .eq("id", str(entry_id))\
            .eq("user_id", str(user_id))\
            .execute()

        return response.data[0] if response.data else None

    async def delete_meal_entry(
        self,
        user_id: UUID,
        entry_id: UUID
    ) -> bool:
        """
        Delete a meal entry.

        Args:
            user_id: User ID
            entry_id: Meal entry ID

        Returns:
            True if deleted, False if not found
        """
        response = self.supabase.table("meal_entries")\
            .delete()\
            .eq("id", str(entry_id))\
            .eq("user_id", str(user_id))\
            .execute()

        return len(response.data) > 0

    # =====================================================
    # HELPER METHODS
    # =====================================================

    def _calculate_summary(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate nutrition summary for a list of meal entries.

        Args:
            entries: List of meal entries

        Returns:
            Summary with totals and percentages
        """
        if not entries:
            return {
                "total_entries": 0,
                "total_calories": 0,
                "total_protein_g": 0,
                "total_carbs_g": 0,
                "total_fat_g": 0,
                "protein_percent": 0,
                "carbs_percent": 0,
                "fat_percent": 0
            }

        total_calories = sum(e["calories"] for e in entries)
        total_protein = sum(Decimal(str(e["protein_g"])) for e in entries)
        total_carbs = sum(Decimal(str(e["carbs_g"])) for e in entries)
        total_fat = sum(Decimal(str(e["fat_g"])) for e in entries)

        # Calculate percentages
        if total_calories > 0:
            protein_cal = float(total_protein) * 4
            carbs_cal = float(total_carbs) * 4
            fat_cal = float(total_fat) * 9

            protein_percent = round((protein_cal / total_calories) * 100, 1)
            carbs_percent = round((carbs_cal / total_calories) * 100, 1)
            fat_percent = round((fat_cal / total_calories) * 100, 1)
        else:
            protein_percent = carbs_percent = fat_percent = 0

        return {
            "total_entries": len(entries),
            "total_calories": total_calories,
            "total_protein_g": float(total_protein),
            "total_carbs_g": float(total_carbs),
            "total_fat_g": float(total_fat),
            "protein_percent": protein_percent,
            "carbs_percent": carbs_percent,
            "fat_percent": fat_percent
        }
