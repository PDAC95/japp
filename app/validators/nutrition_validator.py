"""
Nutrition Data Validator for JAPPI

This module provides strict validation for all nutrition data to ensure:
- No negative values
- Realistic calorie/macro ranges
- Correct macro-to-calorie calculations
- Food quantity constraints

CRITICAL VALIDATIONS (US-036):
- No negative calories or macros
- Calories = (protein×4 + carbs×4 + fat×9) ±5%
- Quantity > 0 grams
- Maximum 5000 calories per food item
- Maximum 2000g per portion
- Water maximum 10 liters (10000ml)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Validation Constants
CALORIES_PER_GRAM_PROTEIN = 4
CALORIES_PER_GRAM_CARBS = 4
CALORIES_PER_GRAM_FAT = 9
CALORIE_TOLERANCE_PERCENT = 0.05  # 5% tolerance

MAX_CALORIES_PER_FOOD = 5000
MAX_PORTION_GRAMS = 2000
MAX_WATER_ML = 10000  # 10 liters
MIN_QUANTITY = 0.01  # Minimum non-zero quantity


@dataclass
class ValidationResult:
    """Result of nutrition validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    corrected_data: Optional[Dict[str, Any]] = None


@dataclass
class FoodValidationError:
    """Error found in food data validation"""
    field: str
    message: str
    severity: str  # 'error' or 'warning'
    original_value: Any
    corrected_value: Optional[Any] = None


class NutritionValidator:
    """
    Comprehensive validator for nutrition data.

    Validates individual food items and complete meal data against
    JAPPI-specific rules and nutrition science constraints.
    """

    def __init__(self):
        """Initialize the nutrition validator."""
        self.errors: List[FoodValidationError] = []
        self.warnings: List[FoodValidationError] = []

    def validate_food_item(
        self,
        food: Dict[str, Any],
        auto_correct: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a single food item.

        Args:
            food: Food item dictionary with nutrition data
            auto_correct: Whether to auto-correct fixable issues

        Returns:
            Tuple of (is_valid, corrected_food_data)

        Validation Rules:
            1. Required fields: name, quantity, calories, protein_g, carbs_g, fat_g
            2. All numeric values must be >= 0
            3. Quantity must be > 0
            4. Calories must match macro calculation ±5%
            5. Calories <= 5000 per item
            6. Portion <= 2000g
        """
        self.errors.clear()
        self.warnings.clear()

        # Deep copy to avoid modifying original
        validated_food = food.copy()

        # Check required fields
        required_fields = ["name", "quantity", "calories", "protein_g", "carbs_g", "fat_g"]
        missing_fields = [f for f in required_fields if f not in food]

        if missing_fields:
            self.errors.append(FoodValidationError(
                field="structure",
                message=f"Missing required fields: {', '.join(missing_fields)}",
                severity="error",
                original_value=food
            ))
            return False, validated_food

        # Validate name
        if not food["name"] or not str(food["name"]).strip():
            self.errors.append(FoodValidationError(
                field="name",
                message="Food name cannot be empty",
                severity="error",
                original_value=food["name"]
            ))
            return False, validated_food

        validated_food["name"] = str(food["name"]).strip()

        # Validate quantity
        try:
            quantity = float(food["quantity"])
            if quantity < 0:
                if auto_correct:
                    quantity = 0
                    self.warnings.append(FoodValidationError(
                        field="quantity",
                        message="Negative quantity corrected to 0",
                        severity="warning",
                        original_value=food["quantity"],
                        corrected_value=0
                    ))
                else:
                    self.errors.append(FoodValidationError(
                        field="quantity",
                        message="Quantity cannot be negative",
                        severity="error",
                        original_value=food["quantity"]
                    ))
                    return False, validated_food

            if quantity == 0 or quantity < MIN_QUANTITY:
                self.errors.append(FoodValidationError(
                    field="quantity",
                    message=f"Quantity must be > {MIN_QUANTITY}",
                    severity="error",
                    original_value=quantity
                ))
                return False, validated_food

            # Check maximum portion size (if unit is in grams/ml)
            unit = str(food.get("unit", "g")).lower()
            if unit in ["g", "grams", "gram"]:
                if quantity > MAX_PORTION_GRAMS:
                    self.warnings.append(FoodValidationError(
                        field="quantity",
                        message=f"Portion size {quantity}g exceeds realistic maximum of {MAX_PORTION_GRAMS}g",
                        severity="warning",
                        original_value=quantity
                    ))
            elif unit in ["ml", "milliliters", "milliliter"]:
                if quantity > MAX_WATER_ML:
                    self.warnings.append(FoodValidationError(
                        field="quantity",
                        message=f"Liquid volume {quantity}ml exceeds maximum of {MAX_WATER_ML}ml",
                        severity="warning",
                        original_value=quantity
                    ))

            validated_food["quantity"] = round(quantity, 2)

        except (ValueError, TypeError) as e:
            self.errors.append(FoodValidationError(
                field="quantity",
                message=f"Invalid quantity value: {e}",
                severity="error",
                original_value=food["quantity"]
            ))
            return False, validated_food

        # Validate calories
        try:
            calories = float(food["calories"])
            if calories < 0:
                if auto_correct:
                    calories = 0
                    self.warnings.append(FoodValidationError(
                        field="calories",
                        message="Negative calories corrected to 0",
                        severity="warning",
                        original_value=food["calories"],
                        corrected_value=0
                    ))
                else:
                    self.errors.append(FoodValidationError(
                        field="calories",
                        message="Calories cannot be negative",
                        severity="error",
                        original_value=food["calories"]
                    ))
                    return False, validated_food

            if calories > MAX_CALORIES_PER_FOOD:
                self.warnings.append(FoodValidationError(
                    field="calories",
                    message=f"Calories {calories} exceeds realistic maximum of {MAX_CALORIES_PER_FOOD}",
                    severity="warning",
                    original_value=calories
                ))

            validated_food["calories"] = round(calories, 2)

        except (ValueError, TypeError) as e:
            self.errors.append(FoodValidationError(
                field="calories",
                message=f"Invalid calories value: {e}",
                severity="error",
                original_value=food["calories"]
            ))
            return False, validated_food

        # Validate macros
        try:
            protein_g = float(food["protein_g"])
            carbs_g = float(food["carbs_g"])
            fat_g = float(food["fat_g"])

            # Check for negatives
            negative_macros = []
            if protein_g < 0:
                negative_macros.append(("protein_g", protein_g))
            if carbs_g < 0:
                negative_macros.append(("carbs_g", carbs_g))
            if fat_g < 0:
                negative_macros.append(("fat_g", fat_g))

            if negative_macros and not auto_correct:
                for field, value in negative_macros:
                    self.errors.append(FoodValidationError(
                        field=field,
                        message=f"{field} cannot be negative",
                        severity="error",
                        original_value=value
                    ))
                return False, validated_food
            elif negative_macros and auto_correct:
                for field, value in negative_macros:
                    self.warnings.append(FoodValidationError(
                        field=field,
                        message=f"Negative {field} corrected to 0",
                        severity="warning",
                        original_value=value,
                        corrected_value=0
                    ))
                protein_g = max(0, protein_g)
                carbs_g = max(0, carbs_g)
                fat_g = max(0, fat_g)

            # Validate macro-to-calorie calculation
            calculated_calories = (
                protein_g * CALORIES_PER_GRAM_PROTEIN +
                carbs_g * CALORIES_PER_GRAM_CARBS +
                fat_g * CALORIES_PER_GRAM_FAT
            )

            tolerance = max(calculated_calories * CALORIE_TOLERANCE_PERCENT, 5)  # Minimum 5 calorie tolerance
            calorie_diff = abs(validated_food["calories"] - calculated_calories)

            if calorie_diff > tolerance:
                if auto_correct:
                    self.warnings.append(FoodValidationError(
                        field="calories",
                        message=f"Calorie mismatch: stated={validated_food['calories']}, "
                                f"calculated={calculated_calories:.1f}. Using calculated value.",
                        severity="warning",
                        original_value=validated_food["calories"],
                        corrected_value=round(calculated_calories, 2)
                    ))
                    validated_food["calories"] = round(calculated_calories, 2)
                else:
                    self.errors.append(FoodValidationError(
                        field="calories",
                        message=f"Calories ({validated_food['calories']}) don't match macro calculation "
                                f"({calculated_calories:.1f}) within {CALORIE_TOLERANCE_PERCENT*100}% tolerance",
                        severity="error",
                        original_value=validated_food["calories"]
                    ))
                    return False, validated_food

            validated_food["protein_g"] = round(protein_g, 2)
            validated_food["carbs_g"] = round(carbs_g, 2)
            validated_food["fat_g"] = round(fat_g, 2)

        except (ValueError, TypeError) as e:
            self.errors.append(FoodValidationError(
                field="macros",
                message=f"Invalid macro values: {e}",
                severity="error",
                original_value={"protein_g": food.get("protein_g"),
                                 "carbs_g": food.get("carbs_g"),
                                 "fat_g": food.get("fat_g")}
            ))
            return False, validated_food

        # Validate unit (optional field)
        if "unit" in food:
            validated_food["unit"] = str(food["unit"]).strip()
        else:
            validated_food["unit"] = "g"  # Default unit

        # All validations passed
        return len(self.errors) == 0, validated_food

    def validate_meal_data(
        self,
        data: Dict[str, Any],
        auto_correct: bool = True
    ) -> ValidationResult:
        """
        Validate complete meal data with multiple food items.

        Args:
            data: Meal data with 'foods' array
            auto_correct: Whether to auto-correct fixable issues

        Returns:
            ValidationResult with validation status and corrected data
        """
        all_errors: List[str] = []
        all_warnings: List[str] = []

        # Check structure
        if "foods" not in data or not isinstance(data["foods"], list):
            return ValidationResult(
                is_valid=False,
                errors=["Invalid data structure: 'foods' array required"],
                warnings=[],
                corrected_data=None
            )

        validated_foods: List[Dict[str, Any]] = []
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        # Validate each food item
        for idx, food in enumerate(data["foods"]):
            is_valid, validated_food = self.validate_food_item(food, auto_correct)

            if not is_valid:
                all_errors.extend([f"Food {idx} ({food.get('name', 'unknown')}): {e.message}"
                                   for e in self.errors])
                continue  # Skip invalid foods

            if self.warnings:
                all_warnings.extend([f"Food {idx} ({food.get('name', 'unknown')}): {w.message}"
                                     for w in self.warnings])

            validated_foods.append(validated_food)

            # Update totals
            total_calories += validated_food["calories"]
            total_protein += validated_food["protein_g"]
            total_carbs += validated_food["carbs_g"]
            total_fat += validated_food["fat_g"]

        # Build corrected data
        corrected_data = {
            "foods": validated_foods,
            "total_calories": round(total_calories, 2),
            "total_macros": {
                "protein": round(total_protein, 2),
                "carbs": round(total_carbs, 2),
                "fat": round(total_fat, 2)
            },
            "message": data.get("message", "Food logged successfully!" if validated_foods else "No valid foods found")
        }

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            corrected_data=corrected_data
        )

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation errors and warnings."""
        return {
            "errors": [
                {
                    "field": e.field,
                    "message": e.message,
                    "original_value": e.original_value,
                    "corrected_value": e.corrected_value
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "field": w.field,
                    "message": w.message,
                    "original_value": w.original_value,
                    "corrected_value": w.corrected_value
                }
                for w in self.warnings
            ],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }


# Singleton instance
_validator: Optional[NutritionValidator] = None


def get_nutrition_validator() -> NutritionValidator:
    """Get or create NutritionValidator singleton instance."""
    global _validator
    if _validator is None:
        _validator = NutritionValidator()
    return _validator
