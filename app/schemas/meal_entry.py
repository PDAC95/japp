"""
Pydantic schemas for meal entry management.

This module defines the data models for meal entries, including:
- Creating new meal entries (manual or from food database)
- Updating existing entries
- Retrieving entries with nutrition summaries
- Daily/weekly aggregations
"""

from datetime import date, datetime
from datetime import time as time_type
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =====================================================
# ENUMS AND CONSTANTS
# =====================================================

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]
LOGGED_VIA_TYPES = ["chat", "voice", "photo", "manual", "barcode"]


# =====================================================
# BASE SCHEMAS
# =====================================================

class MealEntryBase(BaseModel):
    """Base schema for meal entry with common fields."""

    food_name: str = Field(..., min_length=1, max_length=200, description="Name of the food")
    meal_date: date = Field(default_factory=date.today, description="Date of the meal")
    meal_time: time_type = Field(default_factory=lambda: datetime.now().time(), description="Time of the meal")
    meal_type: Optional[str] = Field(None, description="Type: breakfast, lunch, dinner, snack")
    quantity_g: Decimal = Field(..., gt=0, description="Quantity in grams")

    # Nutrition (per serving as consumed)
    calories: int = Field(..., ge=0, description="Total calories")
    protein_g: Decimal = Field(..., ge=0, description="Protein in grams")
    carbs_g: Decimal = Field(..., ge=0, description="Carbs in grams")
    fat_g: Decimal = Field(..., ge=0, description="Fat in grams")

    # Optional metadata
    logged_via: str = Field(default="manual", description="How it was logged")
    original_input: Optional[str] = Field(None, description="Original user input")

    @field_validator('meal_type')
    @classmethod
    def validate_meal_type(cls, v):
        if v and v not in MEAL_TYPES:
            raise ValueError(f"meal_type must be one of {MEAL_TYPES}")
        return v

    @field_validator('logged_via')
    @classmethod
    def validate_logged_via(cls, v):
        if v not in LOGGED_VIA_TYPES:
            raise ValueError(f"logged_via must be one of {LOGGED_VIA_TYPES}")
        return v


# =====================================================
# CREATE SCHEMAS
# =====================================================

class MealEntryCreateManual(MealEntryBase):
    """Create meal entry manually with all nutrition data."""
    pass


class MealEntryCreateFromFood(BaseModel):
    """Create meal entry from existing food in database."""

    food_id: Optional[UUID] = Field(None, description="System food ID")
    user_food_id: Optional[UUID] = Field(None, description="User custom food ID")
    quantity_g: Decimal = Field(..., gt=0, description="Quantity in grams")

    # Optional overrides
    meal_date: date = Field(default_factory=date.today)
    time: time_type = Field(default_factory=lambda: datetime.now().time())
    meal_type: Optional[str] = None
    logged_via: str = Field(default="manual")
    original_input: Optional[str] = None

    @field_validator('meal_type')
    @classmethod
    def validate_meal_type(cls, v):
        if v and v not in MEAL_TYPES:
            raise ValueError(f"meal_type must be one of {MEAL_TYPES}")
        return v

    @field_validator('food_id', 'user_food_id')
    @classmethod
    def validate_food_reference(cls, v, info):
        # Check that at least one is provided
        values = info.data
        if 'food_id' in values and 'user_food_id' in values:
            if not values.get('food_id') and not values.get('user_food_id'):
                raise ValueError("Either food_id or user_food_id must be provided")
            if values.get('food_id') and values.get('user_food_id'):
                raise ValueError("Cannot provide both food_id and user_food_id")
        return v


class MealEntryCreateBatch(BaseModel):
    """Create multiple meal entries at once (for a complete meal)."""

    entries: List[MealEntryCreateFromFood] = Field(..., min_length=1, max_length=50)
    meal_type: Optional[str] = None
    meal_date: date = Field(default_factory=date.today)
    time: time_type = Field(default_factory=lambda: datetime.now().time())
    original_input: Optional[str] = Field(None, description="Original message from chat")


# =====================================================
# UPDATE SCHEMAS
# =====================================================

class MealEntryUpdate(BaseModel):
    """Update an existing meal entry."""

    food_name: Optional[str] = Field(None, min_length=1, max_length=200)
    meal_date: Optional[date] = None
    meal_time: Optional[time_type] = None
    meal_type: Optional[str] = None
    quantity_g: Optional[Decimal] = Field(None, gt=0)

    # Nutrition updates
    calories: Optional[int] = Field(None, ge=0)
    protein_g: Optional[Decimal] = Field(None, ge=0)
    carbs_g: Optional[Decimal] = Field(None, ge=0)
    fat_g: Optional[Decimal] = Field(None, ge=0)

    @field_validator('meal_type')
    @classmethod
    def validate_meal_type(cls, v):
        if v and v not in MEAL_TYPES:
            raise ValueError(f"meal_type must be one of {MEAL_TYPES}")
        return v


# =====================================================
# RESPONSE SCHEMAS
# =====================================================

class MealEntryResponse(BaseModel):
    """Response schema for a single meal entry."""

    id: UUID
    user_id: UUID

    # Food info
    food_name: str
    food_id: Optional[UUID] = None
    user_food_id: Optional[UUID] = None

    # When & what
    meal_date: date
    meal_time: time_type
    meal_type: Optional[str] = None
    quantity_g: Decimal

    # Nutrition
    calories: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal

    # Metadata
    logged_via: str
    original_input: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MealEntrySummary(BaseModel):
    """Nutrition summary for a group of meal entries."""

    total_entries: int
    total_calories: int
    total_protein_g: Decimal
    total_carbs_g: Decimal
    total_fat_g: Decimal

    # Percentages
    protein_percent: float = Field(description="% of calories from protein")
    carbs_percent: float = Field(description="% of calories from carbs")
    fat_percent: float = Field(description="% of calories from fat")


class DailyMealSummary(BaseModel):
    """Complete daily meal summary with breakdown by meal type."""

    meal_date: date

    # Meal entries by type
    breakfast: List[MealEntryResponse] = []
    lunch: List[MealEntryResponse] = []
    dinner: List[MealEntryResponse] = []
    snacks: List[MealEntryResponse] = []

    # Totals
    summary: MealEntrySummary

    # Goal comparison (if user has goals set)
    goal_calories: Optional[int] = None
    remaining_calories: Optional[int] = None
    goal_protein_g: Optional[Decimal] = None
    goal_carbs_g: Optional[Decimal] = None
    goal_fat_g: Optional[Decimal] = None


class MealEntryListResponse(BaseModel):
    """Paginated list of meal entries."""

    items: List[MealEntryResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =====================================================
# FILTER SCHEMAS
# =====================================================

class MealEntryFilters(BaseModel):
    """Filters for querying meal entries."""

    start_date: Optional[date] = Field(None, description="Start date (inclusive)")
    end_date: Optional[date] = Field(None, description="End date (inclusive)")
    meal_type: Optional[str] = Field(None, description="Filter by meal type")
    logged_via: Optional[str] = Field(None, description="Filter by logging method")
    min_calories: Optional[int] = Field(None, ge=0, description="Minimum calories")
    max_calories: Optional[int] = Field(None, ge=0, description="Maximum calories")

    @field_validator('meal_type')
    @classmethod
    def validate_meal_type(cls, v):
        if v and v not in MEAL_TYPES:
            raise ValueError(f"meal_type must be one of {MEAL_TYPES}")
        return v

    @field_validator('logged_via')
    @classmethod
    def validate_logged_via(cls, v):
        if v and v not in LOGGED_VIA_TYPES:
            raise ValueError(f"logged_via must be one of {LOGGED_VIA_TYPES}")
        return v


# =====================================================
# UTILITY SCHEMAS
# =====================================================

class MealTypeClassification(BaseModel):
    """Result of automatic meal type classification."""

    meal_type: str = Field(description="Classified meal type")
    confidence: float = Field(ge=0, le=1, description="Classification confidence")
    reason: str = Field(description="Why this meal type was chosen")


class NutritionValidation(BaseModel):
    """Validation result for nutrition values."""

    is_valid: bool
    discrepancy_percent: float
    message: str
    calculated_calories: float
    provided_calories: float
