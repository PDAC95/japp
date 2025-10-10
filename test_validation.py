"""
Test script for nutrition validation (US-036)

Tests all validation rules:
- No negative values
- Calorie calculation correctness (±5%)
- Quantity > 0
- Maximum constraints (5000 cal, 2000g, 10L)
"""

import sys
sys.path.insert(0, 'C:\\dev\\12j\\apps\\backend')

from app.validators.nutrition_validator import get_nutrition_validator, MAX_CALORIES_PER_FOOD


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """Print formatted test result"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")
    print()


def test_valid_food():
    """Test valid food item with accurate calorie calculation"""
    validator = get_nutrition_validator()

    # Chicken breast: P=46.5g (186cal), C=0g (0cal), F=5.4g (48.6cal)
    # Expected: 186 + 0 + 48.6 = 234.6 calories
    food = {
        "name": "Chicken Breast",
        "quantity": 150,
        "unit": "g",
        "calories": 235,  # Close to calculated value (234.6)
        "protein_g": 46.5,
        "carbs_g": 0,
        "fat_g": 5.4
    }

    is_valid, validated = validator.validate_food_item(food)
    expected_cal = (46.5 * 4) + (0 * 4) + (5.4 * 9)  # 234.6
    passed = is_valid and abs(validated["calories"] - expected_cal) < 5
    print_test_result(
        "Valid food item passes validation",
        passed,
        f"Validated: {validated['name']}, {validated['calories']} cal"
    )


def test_negative_calories():
    """Test negative calories are corrected"""
    validator = get_nutrition_validator()

    food = {
        "name": "Test Food",
        "quantity": 100,
        "calories": -50,  # Negative!
        "protein_g": 10,
        "carbs_g": 20,
        "fat_g": 5
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=True)
    passed = is_valid and validated["calories"] >= 0
    print_test_result(
        "Negative calories auto-corrected",
        passed,
        f"Original: -50, Corrected: {validated['calories']}"
    )


def test_negative_macros():
    """Test negative macros are corrected"""
    validator = get_nutrition_validator()

    food = {
        "name": "Test Food",
        "quantity": 100,
        "calories": 180,
        "protein_g": -10,  # Negative!
        "carbs_g": 20,
        "fat_g": 5
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=True)
    passed = is_valid and all([
        validated["protein_g"] >= 0,
        validated["carbs_g"] >= 0,
        validated["fat_g"] >= 0
    ])
    print_test_result(
        "Negative macros auto-corrected",
        passed,
        f"Protein corrected: {validated['protein_g']}"
    )


def test_calorie_calculation():
    """Test calorie calculation validation (±5%)"""
    validator = get_nutrition_validator()

    # Protein: 10g × 4 = 40
    # Carbs: 20g × 4 = 80
    # Fat: 5g × 9 = 45
    # Total: 165 calories (but stated 200)

    food = {
        "name": "Test Food",
        "quantity": 100,
        "calories": 200,  # Wrong!
        "protein_g": 10,
        "carbs_g": 20,
        "fat_g": 5
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=True)
    expected_cal = (10 * 4) + (20 * 4) + (5 * 9)  # 165
    passed = is_valid and abs(validated["calories"] - expected_cal) < 5
    print_test_result(
        "Incorrect calories auto-corrected to match macros",
        passed,
        f"Stated: 200, Calculated: {expected_cal}, Corrected: {validated['calories']}"
    )


def test_zero_quantity():
    """Test zero quantity is rejected"""
    validator = get_nutrition_validator()

    food = {
        "name": "Test Food",
        "quantity": 0,  # Invalid!
        "calories": 100,
        "protein_g": 10,
        "carbs_g": 10,
        "fat_g": 3
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=False)
    passed = not is_valid
    print_test_result(
        "Zero quantity is rejected",
        passed,
        "Food with 0 quantity cannot be logged"
    )


def test_excessive_calories():
    """Test excessive calories warning"""
    validator = get_nutrition_validator()

    food = {
        "name": "Massive Meal",
        "quantity": 1000,
        "calories": 6000,  # Exceeds MAX_CALORIES_PER_FOOD (5000)
        "protein_g": 100,
        "carbs_g": 700,
        "fat_g": 100
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=True)
    has_warning = len(validator.warnings) > 0
    passed = is_valid and has_warning  # Should pass but with warning
    print_test_result(
        "Excessive calories generate warning",
        passed,
        f"Calories: {validated['calories']}, Warning count: {len(validator.warnings)}"
    )


def test_large_portion():
    """Test large portion warning"""
    validator = get_nutrition_validator()

    food = {
        "name": "Huge Serving",
        "quantity": 3000,  # Exceeds MAX_PORTION_GRAMS (2000)
        "unit": "g",
        "calories": 2000,
        "protein_g": 150,
        "carbs_g": 200,
        "fat_g": 50
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=True)
    has_warning = len(validator.warnings) > 0
    passed = is_valid and has_warning
    print_test_result(
        "Large portion generates warning",
        passed,
        f"Quantity: {validated['quantity']}g, Warning count: {len(validator.warnings)}"
    )


def test_meal_data_validation():
    """Test complete meal validation"""
    validator = get_nutrition_validator()

    meal_data = {
        "foods": [
            {
                "name": "Chicken",
                "quantity": 150,
                "calories": 235,  # Corrected for accurate calculation
                "protein_g": 46.5,
                "carbs_g": 0,
                "fat_g": 5.4
            },
            {
                "name": "Rice",
                "quantity": 200,
                "calories": 260,  # P:5 (20), C:56 (224), F:0.6 (5.4) = 249.4
                "protein_g": 5,
                "carbs_g": 56,
                "fat_g": 0.6
            }
        ]
    }

    result = validator.validate_meal_data(meal_data, auto_correct=True)
    total_cal = result.corrected_data["total_calories"]
    # Expected: Chicken ~235 + Rice ~249 = ~484
    expected_total = (46.5*4) + (5.4*9) + (5*4) + (56*4) + (0.6*9)  # 484
    # Allow small rounding differences
    passed = result.is_valid and abs(total_cal - expected_total) < 15
    print_test_result(
        "Complete meal validation",
        passed,
        f"Total calories: {total_cal}, Foods: {len(result.corrected_data['foods'])}"
    )


def test_missing_fields():
    """Test missing required fields"""
    validator = get_nutrition_validator()

    food = {
        "name": "Incomplete",
        "quantity": 100
        # Missing: calories, protein_g, carbs_g, fat_g
    }

    is_valid, validated = validator.validate_food_item(food, auto_correct=True)
    passed = not is_valid
    print_test_result(
        "Missing required fields rejected",
        passed,
        f"Error count: {len(validator.errors)}"
    )


def run_all_tests():
    """Run all validation tests"""
    print("="*60)
    print("NUTRITION VALIDATION TESTS (US-036)")
    print("="*60)
    print()

    test_valid_food()
    test_negative_calories()
    test_negative_macros()
    test_calorie_calculation()
    test_zero_quantity()
    test_excessive_calories()
    test_large_portion()
    test_meal_data_validation()
    test_missing_fields()

    print("="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
