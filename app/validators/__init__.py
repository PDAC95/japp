"""
Validators package for JAPPI backend.

Contains validation logic for:
- Nutrition data (calories, macros)
- Food items and portions
- Meal entries
- User input constraints
"""

from app.validators.nutrition_validator import (
    NutritionValidator,
    ValidationResult,
    FoodValidationError,
    get_nutrition_validator,
    CALORIES_PER_GRAM_PROTEIN,
    CALORIES_PER_GRAM_CARBS,
    CALORIES_PER_GRAM_FAT,
    CALORIE_TOLERANCE_PERCENT,
    MAX_CALORIES_PER_FOOD,
    MAX_PORTION_GRAMS,
    MAX_WATER_ML,
)

__all__ = [
    "NutritionValidator",
    "ValidationResult",
    "FoodValidationError",
    "get_nutrition_validator",
    "CALORIES_PER_GRAM_PROTEIN",
    "CALORIES_PER_GRAM_CARBS",
    "CALORIES_PER_GRAM_FAT",
    "CALORIE_TOLERANCE_PERCENT",
    "MAX_CALORIES_PER_FOOD",
    "MAX_PORTION_GRAMS",
    "MAX_WATER_ML",
]
