"""
Macro calculation service with JAPPI-specific validations.

Handles all nutrition calculations, unit conversions, aggregations,
and goal comparisons.
"""

from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


# =====================================================
# CONSTANTS
# =====================================================

# Calorie factors (calories per gram)
PROTEIN_CAL_PER_G = 4
CARBS_CAL_PER_G = 4
FAT_CAL_PER_G = 9

# Validation thresholds
CALORIE_TOLERANCE_PERCENT = 5.0  # 5% tolerance for calorie calculation
MAX_CALORIES_PER_MEAL = 3000  # Maximum realistic calories per meal
MAX_DAILY_CALORIES = 10000  # Maximum realistic daily calories
MIN_MACRO_PERCENTAGE = 0  # Minimum percentage for a macro
MAX_MACRO_PERCENTAGE = 100  # Maximum percentage for a macro


# =====================================================
# CORE CALCULATION FUNCTIONS
# =====================================================


def calculate_calories_from_macros(
    protein_g: float, carbs_g: float, fat_g: float
) -> float:
    """
    Calculate total calories from macronutrients.

    Formula: (Protein × 4) + (Carbs × 4) + (Fat × 9)

    Args:
        protein_g: Protein in grams
        carbs_g: Carbohydrates in grams
        fat_g: Fat in grams

    Returns:
        Total calories (rounded to 2 decimals)
    """
    if protein_g < 0 or carbs_g < 0 or fat_g < 0:
        raise ValueError("Macro values cannot be negative")

    calories = (protein_g * PROTEIN_CAL_PER_G) + (carbs_g * CARBS_CAL_PER_G) + (
        fat_g * FAT_CAL_PER_G
    )

    return round(calories, 2)


def validate_calorie_calculation(
    provided_calories: float, protein_g: float, carbs_g: float, fat_g: float
) -> Tuple[bool, float, str]:
    """
    Validate that provided calories match calculated calories within tolerance.

    Args:
        provided_calories: Calories as stated
        protein_g: Protein in grams
        carbs_g: Carbohydrates in grams
        fat_g: Fat in grams

    Returns:
        Tuple of (is_valid, discrepancy_percent, message)
    """
    calculated_calories = calculate_calories_from_macros(protein_g, carbs_g, fat_g)

    if calculated_calories == 0:
        return (True, 0.0, "No macros provided")

    discrepancy = abs(provided_calories - calculated_calories)
    discrepancy_percent = (discrepancy / calculated_calories) * 100

    is_valid = discrepancy_percent <= CALORIE_TOLERANCE_PERCENT

    if is_valid:
        message = f"Calorie calculation valid (within {CALORIE_TOLERANCE_PERCENT}% tolerance)"
    else:
        message = (
            f"Calorie mismatch: Provided {provided_calories} cal, "
            f"Calculated {calculated_calories} cal "
            f"(discrepancy: {discrepancy_percent:.1f}%)"
        )

    return (is_valid, discrepancy_percent, message)


def calculate_macro_percentages(
    protein_g: float, carbs_g: float, fat_g: float
) -> Dict[str, float]:
    """
    Calculate percentage of calories from each macronutrient.

    Args:
        protein_g: Protein in grams
        carbs_g: Carbohydrates in grams
        fat_g: Fat in grams

    Returns:
        Dictionary with percentages: {protein_pct, carbs_pct, fat_pct}
    """
    total_calories = calculate_calories_from_macros(protein_g, carbs_g, fat_g)

    if total_calories == 0:
        return {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

    protein_calories = protein_g * PROTEIN_CAL_PER_G
    carbs_calories = carbs_g * CARBS_CAL_PER_G
    fat_calories = fat_g * FAT_CAL_PER_G

    return {
        "protein_pct": round((protein_calories / total_calories) * 100, 1),
        "carbs_pct": round((carbs_calories / total_calories) * 100, 1),
        "fat_pct": round((fat_calories / total_calories) * 100, 1),
    }


# =====================================================
# UNIT CONVERSION
# =====================================================


def convert_to_grams(quantity: float, unit: str, serving_size_g: float = 100) -> float:
    """
    Convert various units to grams.

    Supported units:
    - g, grams, gramos
    - kg, kilograms, kilogramos
    - oz, ounces, onzas
    - lb, pounds, libras
    - cup, taza (uses serving_size_g)
    - tbsp, tablespoon, cucharada (15g)
    - tsp, teaspoon, cucharadita (5g)
    - piece, pieza (uses serving_size_g)
    - serving, porción (uses serving_size_g)

    Args:
        quantity: Numeric quantity
        unit: Unit string
        serving_size_g: Default serving size in grams (for cup, piece, etc.)

    Returns:
        Quantity in grams
    """
    unit_lower = unit.lower().strip()

    # Weight units
    if unit_lower in ["g", "grams", "gramos", "gr"]:
        return quantity
    elif unit_lower in ["kg", "kilograms", "kilogramos"]:
        return quantity * 1000
    elif unit_lower in ["oz", "ounces", "onzas"]:
        return quantity * 28.35
    elif unit_lower in ["lb", "lbs", "pounds", "libras"]:
        return quantity * 453.592

    # Volume/serving units (use serving_size_g)
    elif unit_lower in ["cup", "taza", "cups", "tazas"]:
        return quantity * serving_size_g
    elif unit_lower in ["piece", "pieza", "pieces", "piezas", "unidad", "unidades"]:
        return quantity * serving_size_g
    elif unit_lower in ["serving", "porción", "porciones", "servings"]:
        return quantity * serving_size_g

    # Spoon measurements
    elif unit_lower in ["tbsp", "tablespoon", "cucharada", "cucharadas"]:
        return quantity * 15
    elif unit_lower in ["tsp", "teaspoon", "cucharadita", "cucharaditas"]:
        return quantity * 5

    else:
        # Default: assume grams
        logger.warning(f"Unknown unit '{unit}', assuming grams")
        return quantity


def scale_nutrition(
    base_nutrition: Dict[str, float], base_quantity_g: float, actual_quantity_g: float
) -> Dict[str, float]:
    """
    Scale nutrition values from base quantity to actual quantity.

    Args:
        base_nutrition: Nutrition per base_quantity_g (usually 100g)
        base_quantity_g: Base quantity (e.g., 100g)
        actual_quantity_g: Actual quantity consumed

    Returns:
        Scaled nutrition values
    """
    scale_factor = actual_quantity_g / base_quantity_g

    return {
        "calories": round(base_nutrition.get("calories", 0) * scale_factor, 2),
        "protein_g": round(base_nutrition.get("protein_g", 0) * scale_factor, 2),
        "carbs_g": round(base_nutrition.get("carbs_g", 0) * scale_factor, 2),
        "fat_g": round(base_nutrition.get("fat_g", 0) * scale_factor, 2),
        "fiber_g": round(base_nutrition.get("fiber_g", 0) * scale_factor, 2),
        "sugar_g": round(base_nutrition.get("sugar_g", 0) * scale_factor, 2),
        "sodium_mg": round(base_nutrition.get("sodium_mg", 0) * scale_factor, 2),
    }


# =====================================================
# MEAL AGGREGATION
# =====================================================


def aggregate_meal_nutrition(meal_items: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Aggregate nutrition from multiple food items in a meal.

    Args:
        meal_items: List of food items with nutrition data
        Each item should have: calories, protein_g, carbs_g, fat_g

    Returns:
        Aggregated nutrition totals
    """
    totals = {
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
        "sodium_mg": 0.0,
    }

    for item in meal_items:
        totals["calories"] += float(item.get("calories", 0))
        totals["protein_g"] += float(item.get("protein_g", 0))
        totals["carbs_g"] += float(item.get("carbs_g", 0))
        totals["fat_g"] += float(item.get("fat_g", 0))
        totals["fiber_g"] += float(item.get("fiber_g", 0))
        totals["sugar_g"] += float(item.get("sugar_g", 0))
        totals["sodium_mg"] += float(item.get("sodium_mg", 0))

    # Round all values
    return {key: round(value, 2) for key, value in totals.items()}


def validate_meal_totals(totals: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Validate meal totals against JAPPI-specific rules.

    Rules:
    1. No negative values
    2. Calories match macro calculation (within 5%)
    3. Total calories <= MAX_CALORIES_PER_MEAL

    Args:
        totals: Meal nutrition totals

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check for negative values
    for key, value in totals.items():
        if value < 0:
            errors.append(f"{key} cannot be negative ({value})")

    # Check calorie calculation
    is_valid, discrepancy, message = validate_calorie_calculation(
        totals["calories"], totals["protein_g"], totals["carbs_g"], totals["fat_g"]
    )

    if not is_valid:
        errors.append(message)

    # Check maximum calories
    if totals["calories"] > MAX_CALORIES_PER_MEAL:
        errors.append(
            f"Meal calories ({totals['calories']}) exceed maximum ({MAX_CALORIES_PER_MEAL})"
        )

    return (len(errors) == 0, errors)


# =====================================================
# DAILY CALCULATIONS
# =====================================================


def calculate_daily_summary(
    meal_entries: List[Dict[str, Any]], goals: Dict[str, float]
) -> Dict[str, Any]:
    """
    Calculate daily nutrition summary and compare to goals.

    Args:
        meal_entries: List of all meals for the day
        goals: Daily nutrition goals {calories, protein_g, carbs_g, fat_g}

    Returns:
        Summary with totals, percentages, and goal comparison
    """
    # Aggregate all meals
    totals = aggregate_meal_nutrition(meal_entries)

    # Calculate macro percentages
    percentages = calculate_macro_percentages(
        totals["protein_g"], totals["carbs_g"], totals["fat_g"]
    )

    # Compare to goals
    comparison = {
        "calories_consumed": totals["calories"],
        "calories_goal": goals.get("calories", 2000),
        "calories_remaining": goals.get("calories", 2000) - totals["calories"],
        "protein_consumed": totals["protein_g"],
        "protein_goal": goals.get("protein_g", 150),
        "protein_remaining": goals.get("protein_g", 150) - totals["protein_g"],
        "carbs_consumed": totals["carbs_g"],
        "carbs_goal": goals.get("carbs_g", 200),
        "carbs_remaining": goals.get("carbs_g", 200) - totals["carbs_g"],
        "fat_consumed": totals["fat_g"],
        "fat_goal": goals.get("fat_g", 65),
        "fat_remaining": goals.get("fat_g", 65) - totals["fat_g"],
    }

    # Calculate goal percentages
    goal_percentages = {
        "calories_pct": round(
            (totals["calories"] / comparison["calories_goal"]) * 100, 1
        )
        if comparison["calories_goal"] > 0
        else 0,
        "protein_pct": round(
            (totals["protein_g"] / comparison["protein_goal"]) * 100, 1
        )
        if comparison["protein_goal"] > 0
        else 0,
        "carbs_pct": round(
            (totals["carbs_g"] / comparison["carbs_goal"]) * 100, 1
        )
        if comparison["carbs_goal"] > 0
        else 0,
        "fat_pct": round((totals["fat_g"] / comparison["fat_goal"]) * 100, 1)
        if comparison["fat_goal"] > 0
        else 0,
    }

    return {
        "totals": totals,
        "macro_percentages": percentages,
        "goal_comparison": comparison,
        "goal_percentages": goal_percentages,
        "is_over_goal": totals["calories"] > comparison["calories_goal"],
        "is_under_goal": totals["calories"] < comparison["calories_goal"],
    }


def calculate_weekly_average(
    daily_summaries: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate weekly average nutrition from daily summaries.

    Args:
        daily_summaries: List of daily summaries (up to 7 days)

    Returns:
        Weekly averages
    """
    if not daily_summaries:
        return {
            "avg_calories": 0.0,
            "avg_protein_g": 0.0,
            "avg_carbs_g": 0.0,
            "avg_fat_g": 0.0,
        }

    num_days = len(daily_summaries)

    total_calories = sum(
        day["totals"]["calories"] for day in daily_summaries if "totals" in day
    )
    total_protein = sum(
        day["totals"]["protein_g"] for day in daily_summaries if "totals" in day
    )
    total_carbs = sum(
        day["totals"]["carbs_g"] for day in daily_summaries if "totals" in day
    )
    total_fat = sum(
        day["totals"]["fat_g"] for day in daily_summaries if "totals" in day
    )

    return {
        "avg_calories": round(total_calories / num_days, 2),
        "avg_protein_g": round(total_protein / num_days, 2),
        "avg_carbs_g": round(total_carbs / num_days, 2),
        "avg_fat_g": round(total_fat / num_days, 2),
    }


def project_daily_total(
    consumed_so_far: Dict[str, float], current_time_hours: int
) -> Dict[str, float]:
    """
    Project end-of-day totals based on consumption so far.

    Assumes linear consumption throughout the day.

    Args:
        consumed_so_far: Nutrition consumed up to current time
        current_time_hours: Current hour (0-23)

    Returns:
        Projected daily totals
    """
    if current_time_hours == 0:
        current_time_hours = 1  # Avoid division by zero

    hours_in_day = 24
    projection_factor = hours_in_day / current_time_hours

    return {
        "projected_calories": round(
            consumed_so_far.get("calories", 0) * projection_factor, 2
        ),
        "projected_protein_g": round(
            consumed_so_far.get("protein_g", 0) * projection_factor, 2
        ),
        "projected_carbs_g": round(
            consumed_so_far.get("carbs_g", 0) * projection_factor, 2
        ),
        "projected_fat_g": round(
            consumed_so_far.get("fat_g", 0) * projection_factor, 2
        ),
    }


# =====================================================
# MACRO SERVICE CLASS
# =====================================================


class MacroCalculationService:
    """
    Service for all macro calculation operations.

    Provides methods for:
    - Calorie calculation and validation
    - Unit conversion
    - Meal aggregation
    - Daily summaries
    - Goal comparisons
    - Weekly averages
    """

    @staticmethod
    def calculate_meal_nutrition(
        food_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate nutrition for a complete meal.

        Args:
            food_items: List of foods with quantities

        Returns:
            Meal nutrition with totals and validation
        """
        # Aggregate nutrition
        totals = aggregate_meal_nutrition(food_items)

        # Validate
        is_valid, errors = validate_meal_totals(totals)

        # Calculate percentages
        percentages = calculate_macro_percentages(
            totals["protein_g"], totals["carbs_g"], totals["fat_g"]
        )

        return {
            "totals": totals,
            "macro_percentages": percentages,
            "is_valid": is_valid,
            "validation_errors": errors,
        }

    @staticmethod
    def calculate_food_nutrition_for_quantity(
        food: Dict[str, Any], quantity: float, unit: str = "g"
    ) -> Dict[str, float]:
        """
        Calculate nutrition for a specific quantity of food.

        Args:
            food: Food data with nutrition per 100g
            quantity: Quantity consumed
            unit: Unit of measurement

        Returns:
            Scaled nutrition values
        """
        # Convert to grams
        quantity_g = convert_to_grams(
            quantity, unit, food.get("serving_size_g", 100)
        )

        # Scale nutrition from 100g base to actual quantity
        return scale_nutrition(
            base_nutrition={
                "calories": float(food.get("calories", 0)),
                "protein_g": float(food.get("protein_g", 0)),
                "carbs_g": float(food.get("carbs_g", 0)),
                "fat_g": float(food.get("fat_g", 0)),
                "fiber_g": float(food.get("fiber_g", 0)),
                "sugar_g": float(food.get("sugar_g", 0)),
                "sodium_mg": float(food.get("sodium_mg", 0)),
            },
            base_quantity_g=100,  # Nutrition data is per 100g
            actual_quantity_g=quantity_g,
        )

    @staticmethod
    def get_daily_summary(
        meal_entries: List[Dict[str, Any]], goals: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Get complete daily summary with goal comparison.

        Args:
            meal_entries: All meals for the day
            goals: Daily nutrition goals

        Returns:
            Complete daily summary
        """
        return calculate_daily_summary(meal_entries, goals)

    @staticmethod
    def get_weekly_average(
        daily_summaries: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate weekly averages.

        Args:
            daily_summaries: List of daily summaries

        Returns:
            Weekly averages
        """
        return calculate_weekly_average(daily_summaries)
