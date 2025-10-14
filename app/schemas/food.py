"""
Food-related Pydantic schemas for request/response validation.

Schemas for food search, CRUD operations, and nutrition data.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime


# =====================================================
# BASE SCHEMAS
# =====================================================


class FoodBase(BaseModel):
    """Base food schema with common fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Food name")
    name_en: Optional[str] = Field(None, max_length=200, description="English name")
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field(
        ...,
        description="Food category: protein, grain, vegetable, fruit, dairy, snack",
    )
    brand_id: Optional[str] = Field(None, description="Brand UUID")
    barcode: Optional[str] = Field(None, max_length=50)

    # Nutrition per 100g
    calories: Decimal = Field(..., ge=0, description="Calories per 100g")
    protein_g: Decimal = Field(0, ge=0, description="Protein in grams")
    carbs_g: Decimal = Field(0, ge=0, description="Carbohydrates in grams")
    fat_g: Decimal = Field(0, ge=0, description="Fat in grams")

    # Additional macros
    fiber_g: Optional[Decimal] = Field(0, ge=0, description="Fiber in grams")
    sugar_g: Optional[Decimal] = Field(0, ge=0, description="Sugar in grams")
    saturated_fat_g: Optional[Decimal] = Field(0, ge=0, description="Saturated fat")
    trans_fat_g: Optional[Decimal] = Field(0, ge=0, description="Trans fat")

    # Micronutrients
    sodium_mg: Optional[Decimal] = Field(0, ge=0, description="Sodium in mg")
    potassium_mg: Optional[Decimal] = Field(0, ge=0, description="Potassium in mg")
    cholesterol_mg: Optional[Decimal] = Field(0, ge=0, description="Cholesterol in mg")

    # Serving info
    serving_size_g: Decimal = Field(100, ge=0, description="Default serving size")
    serving_size_description: Optional[str] = Field(
        None, max_length=100, description="e.g., '1 cup', '1 piece'"
    )

    # Additional info
    allergens: Optional[List[str]] = Field(
        None, description="List of allergens: gluten, dairy, nuts, etc."
    )
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False

    @validator("calories")
    def validate_calories(cls, v, values):
        """Validate calories match macro calculation within 10% tolerance."""
        if "protein_g" in values and "carbs_g" in values and "fat_g" in values:
            protein = float(values["protein_g"])
            carbs = float(values["carbs_g"])
            fat = float(values["fat_g"])

            calculated = (protein * 4) + (carbs * 4) + (fat * 9)
            tolerance = calculated * 0.10  # 10% tolerance

            if abs(float(v) - calculated) > tolerance:
                raise ValueError(
                    f"Calorie calculation mismatch: Provided {v} cal, "
                    f"Calculated {calculated:.2f} cal (tolerance: ±{tolerance:.2f})"
                )

        return v


# =====================================================
# FOOD SCHEMAS (System Foods)
# =====================================================


class FoodCreate(FoodBase):
    """Schema for creating a new system food."""

    verified: bool = False
    source: str = Field("manual", description="Data source: usda, manual, api")


class FoodUpdate(BaseModel):
    """Schema for updating a system food (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    calories: Optional[Decimal] = Field(None, ge=0)
    protein_g: Optional[Decimal] = Field(None, ge=0)
    carbs_g: Optional[Decimal] = Field(None, ge=0)
    fat_g: Optional[Decimal] = Field(None, ge=0)
    verified: Optional[bool] = None


class FoodResponse(FoodBase):
    """Schema for food response with database fields."""

    id: str = Field(..., description="Food UUID")
    verified: bool
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# USER FOOD SCHEMAS (Custom Foods)
# =====================================================


class UserFoodCreate(BaseModel):
    """Schema for creating a custom user food."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str
    brand_id: Optional[str] = None

    # Nutrition per 100g (required)
    calories: Decimal = Field(..., ge=0)
    protein_g: Decimal = Field(0, ge=0)
    carbs_g: Decimal = Field(0, ge=0)
    fat_g: Decimal = Field(0, ge=0)

    # Additional (optional)
    fiber_g: Optional[Decimal] = Field(0, ge=0)
    sugar_g: Optional[Decimal] = Field(0, ge=0)
    saturated_fat_g: Optional[Decimal] = Field(0, ge=0)
    sodium_mg: Optional[Decimal] = Field(0, ge=0)

    # Serving
    serving_size_g: Decimal = Field(100, ge=0)
    serving_size_description: Optional[str] = None

    # Privacy
    is_public: bool = False

    @validator("calories")
    def validate_calories(cls, v, values):
        """Validate calories match macro calculation within 10% tolerance."""
        if "protein_g" in values and "carbs_g" in values and "fat_g" in values:
            protein = float(values["protein_g"])
            carbs = float(values["carbs_g"])
            fat = float(values["fat_g"])

            calculated = (protein * 4) + (carbs * 4) + (fat * 9)
            tolerance = calculated * 0.10

            if abs(float(v) - calculated) > tolerance:
                raise ValueError(
                    f"Calorie calculation mismatch: Provided {v} cal, "
                    f"Calculated {calculated:.2f} cal (tolerance: ±{tolerance:.2f})"
                )

        return v


class UserFoodResponse(BaseModel):
    """Schema for user food response."""

    id: str
    user_id: str
    name: str
    description: Optional[str]
    category: str
    brand_id: Optional[str]

    # Nutrition
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Optional[Decimal]
    sugar_g: Optional[Decimal]
    saturated_fat_g: Optional[Decimal]
    sodium_mg: Optional[Decimal]

    # Serving
    serving_size_g: Decimal
    serving_size_description: Optional[str]

    # Privacy
    is_public: bool

    # Metadata
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# FOOD SEARCH SCHEMAS
# =====================================================


class FoodSearchFilters(BaseModel):
    """Optional filters for food search."""

    category: Optional[str] = Field(
        None, description="Filter by category: protein, grain, vegetable, etc."
    )
    brand_id: Optional[str] = Field(None, description="Filter by brand UUID")
    only_user_foods: bool = Field(
        False, description="Only return user's custom foods"
    )
    min_calories: Optional[Decimal] = Field(None, ge=0, description="Minimum calories")
    max_calories: Optional[Decimal] = Field(
        None, ge=0, description="Maximum calories"
    )
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_gluten_free: Optional[bool] = None


class FoodSearchRequest(BaseModel):
    """Request schema for food search."""

    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    page: int = Field(1, ge=1, description="Page number (starts at 1)")
    page_size: int = Field(
        20, ge=1, le=100, description="Items per page (max 100)"
    )
    filters: Optional[FoodSearchFilters] = None


class FoodSearchResultItem(BaseModel):
    """Single food search result item."""

    id: str = Field(..., description="Food or UserFood UUID")
    source: str = Field(
        ..., description="Source: 'system', 'user', 'favorite', 'user_favorite'"
    )
    name: str
    name_en: Optional[str] = None
    category: str
    brand_name: Optional[str] = None

    # Nutrition
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal

    # Serving
    serving_size_g: Decimal
    serving_size_description: Optional[str] = None

    # Metadata
    is_favorite: bool = False
    use_count: Optional[int] = Field(
        None, description="Usage count if in favorites"
    )
    relevance_score: float = Field(
        ..., ge=0, le=1, description="Search relevance (0-1)"
    )

    class Config:
        from_attributes = True


class FoodSearchResponse(BaseModel):
    """Response schema for food search with pagination."""

    success: bool = True
    data: List[FoodSearchResultItem]
    pagination: dict = Field(
        ...,
        description="Pagination info: page, page_size, total_items, total_pages, has_more",
    )
    message: Optional[str] = None


# =====================================================
# FOOD FAVORITES SCHEMAS
# =====================================================


class FoodFavoriteCreate(BaseModel):
    """Schema for adding a food to favorites."""

    food_id: Optional[str] = Field(None, description="System food UUID")
    user_food_id: Optional[str] = Field(None, description="Custom food UUID")

    @validator("user_food_id")
    def validate_one_id(cls, v, values):
        """Ensure either food_id OR user_food_id is set, not both."""
        food_id = values.get("food_id")

        if not food_id and not v:
            raise ValueError("Either food_id or user_food_id must be provided")

        if food_id and v:
            raise ValueError("Only one of food_id or user_food_id can be set")

        return v


class FoodFavoriteResponse(BaseModel):
    """Schema for food favorite response."""

    id: str
    user_id: str
    food_id: Optional[str]
    user_food_id: Optional[str]
    use_count: int
    last_used_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# BRAND SCHEMAS
# =====================================================


class BrandCreate(BaseModel):
    """Schema for creating a food brand."""

    name: str = Field(..., min_length=1, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = None


class BrandResponse(BaseModel):
    """Schema for brand response."""

    id: str
    name: str
    country: Optional[str]
    website: Optional[str]
    verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
