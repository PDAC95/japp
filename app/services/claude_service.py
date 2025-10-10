"""
Claude AI Integration Service for JAPPI

This service handles all interactions with Anthropic's Claude API for:
- Natural language food extraction
- Nutrition data parsing
- Conversational coaching responses

CRITICAL VALIDATIONS (per CLAUDE.md):
- Never allow negative nutrition values
- Always validate food quantities > 0
- Timeout maximum 30 seconds
- Response always in valid JSON format
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from anthropic import AsyncAnthropic
from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.validators.nutrition_validator import get_nutrition_validator

logger = logging.getLogger(__name__)


class ClaudeService:
    """
    Service for interacting with Claude API.

    Handles food extraction, nutrition parsing, and coaching responses
    with proper error handling and validation.
    """

    def __init__(self):
        """Initialize Claude client with API key from environment."""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured in environment")

        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=30.0  # Maximum 30 seconds as per requirements
        )
        self.model = settings.CLAUDE_MODEL or "claude-3-5-sonnet-20241022"
        self.max_tokens = settings.CLAUDE_MAX_TOKENS or 2000
        self.temperature = settings.CLAUDE_TEMPERATURE or 0.3  # Lower for consistency
        self.supabase = get_supabase_client()

        logger.info(f"ClaudeService initialized with model: {self.model}")

    async def _get_personality_instructions(self, personality_code: str) -> str:
        """
        Get prompt instructions for a personality from database.

        Args:
            personality_code: Personality code (e.g., 'friendly', 'strict')

        Returns:
            Prompt instructions string

        Fallback to friendly if personality not found.
        """
        try:
            response = self.supabase.table('personality_types') \
                .select('prompt_instructions') \
                .eq('code', personality_code) \
                .eq('is_active', True) \
                .single() \
                .execute()

            if response.data:
                logger.info(f"Loaded personality '{personality_code}' from database")
                return response.data['prompt_instructions']

        except Exception as e:
            logger.warning(f"Failed to load personality '{personality_code}' from DB: {e}")

        # Fallback to friendly
        try:
            response = self.supabase.table('personality_types') \
                .select('prompt_instructions') \
                .eq('code', 'friendly') \
                .eq('is_active', True) \
                .single() \
                .execute()

            if response.data:
                logger.info("Using fallback personality 'friendly'")
                return response.data['prompt_instructions']

        except Exception as e:
            logger.error(f"Failed to load fallback personality: {e}")

        # Final hardcoded fallback
        return "You are a warm, supportive nutrition coach. Be encouraging and understanding."

    async def extract_food_from_text(
        self,
        text: str,
        personality: str = 'friendly',
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Extract food items and nutrition data from natural language text.

        Args:
            text: User's natural language food description
                  Examples: "Comí 2 tacos de carnitas", "3 eggs and toast"
            personality: Coach personality type (friendly, strict, motivational, casual)
            max_retries: Maximum retry attempts with exponential backoff

        Returns:
            Dict containing:
                - foods: List[Dict] with name, quantity, unit, calories, macros
                - total_calories: int
                - total_macros: Dict with protein, carbs, fat
                - message: Optional coaching message
                - error: Optional error message if extraction failed

        Raises:
            ValueError: If text is empty or invalid
            TimeoutError: If API call exceeds 30 seconds
        """
        if not text or not text.strip():
            raise ValueError("Food description text cannot be empty")

        # Build optimized prompt for food extraction with personality
        prompt = await self._build_food_extraction_prompt(text, personality)

        # Call Claude with retry logic
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Claude API (attempt {attempt + 1}/{max_retries})")

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                # Extract text content from response
                if not response.content or len(response.content) == 0:
                    raise ValueError("Empty response from Claude")

                raw_text = response.content[0].text
                logger.debug(f"Claude raw response: {raw_text}")

                # Parse JSON response
                parsed_data = self._parse_claude_response(raw_text)

                # CRITICAL: Validate nutrition data with enhanced validator (US-036)
                validated_data = self._validate_nutrition_data_v2(parsed_data)

                logger.info(f"Successfully extracted {len(validated_data['foods'])} food items")
                return validated_data

            except TimeoutError:
                logger.error(f"Claude API timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    return {
                        "foods": [],
                        "total_calories": 0,
                        "total_macros": {"protein": 0, "carbs": 0, "fat": 0},
                        "error": "API timeout - please try again"
                    }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Claude response as JSON: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return {
                        "foods": [],
                        "total_calories": 0,
                        "total_macros": {"protein": 0, "carbs": 0, "fat": 0},
                        "error": "Could not understand food description"
                    }

            except Exception as e:
                logger.error(f"Unexpected error calling Claude: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return {
                        "foods": [],
                        "total_calories": 0,
                        "total_macros": {"protein": 0, "carbs": 0, "fat": 0},
                        "error": "Failed to process your request"
                    }

        # Should not reach here, but safety fallback
        return {
            "foods": [],
            "total_calories": 0,
            "total_macros": {"protein": 0, "carbs": 0, "fat": 0},
            "error": "Maximum retries exceeded"
        }

    async def _build_food_extraction_prompt(self, text: str, personality: str = 'friendly') -> str:
        """
        Build optimized prompt for extracting food data with personality.

        Designed to handle:
        - North American foods (burgers, sandwiches, salads, etc.)
        - Common measurements (cups, tablespoons, ounces, pieces)
        - International cuisine (Mexican, Italian, Asian, etc.)
        - English descriptions (primary market: USA/Canada)
        - Personality-based responses (loaded dynamically from database)
        """

        # Load personality instructions from database
        personality_instructions = await self._get_personality_instructions(personality)

        return f"""You are JAPPI, an AI nutrition coach that extracts food information from natural language.

PERSONALITY INSTRUCTIONS:
{personality_instructions}

USER INPUT: "{text}"

Extract all foods mentioned and estimate their nutrition data. Return ONLY valid JSON (no markdown, no explanations).

JSON FORMAT:
{{
  "foods": [
    {{
      "name": "food name",
      "quantity": number,
      "unit": "g" | "ml" | "oz" | "piece" | "cup" | "tbsp" | "serving",
      "calories": number (must be >= 0),
      "protein_g": number (must be >= 0),
      "carbs_g": number (must be >= 0),
      "fat_g": number (must be >= 0)
    }}
  ],
  "message": "optional response based on personality"
}}

RULES:
1. All nutrition values MUST be >= 0 (never negative)
2. Understand North American portion sizes and common foods
3. Estimate reasonable portions based on typical US/Canadian servings
4. Convert colloquial measurements to standard units (1 cup ~240ml, 1 tbsp ~15ml, 1 oz ~28g)
5. Calculate calories accurately: (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
6. If unsure, provide conservative estimates
7. Return ONLY the JSON object, nothing else
8. Recognize common restaurant chains and their typical portions
9. IMPORTANT: Include a "message" field with a personality-appropriate response

COMMON FOODS & PORTIONS (USA/Canada):
- "burger" → ~500-800 calories (depends on type)
- "chicken breast" (6oz) → ~280 calories
- "scrambled eggs" (2 eggs) → ~200 calories
- "toast with butter" (2 slices) → ~200 calories
- "protein shake" → ~150-300 calories
- "salad with dressing" → ~200-400 calories
- "sandwich" → ~300-600 calories
- "bowl of cereal with milk" → ~200-300 calories
- "apple" (medium) → ~95 calories
- "banana" (medium) → ~105 calories

EXAMPLES:
- "3 eggs and toast" → eggs ~210 cal, toast ~160 cal
- "grilled chicken breast with rice" → chicken ~280 cal, rice (1 cup) ~200 cal
- "turkey sandwich on whole wheat" → ~400 calories
- "greek yogurt with berries" → yogurt ~150 cal, berries ~50 cal

Now extract from: "{text}"
"""

    def _parse_claude_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse Claude's text response into structured JSON.

        Handles:
        - Markdown code blocks
        - Extra whitespace
        - Invalid JSON
        """
        # Remove markdown code blocks if present
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        if text.startswith("```"):
            text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```

        text = text.strip()

        # Parse JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON object from text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                raise

        return data

    def _validate_nutrition_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize nutrition data.

        CRITICAL VALIDATION (per CLAUDE.md):
        - No negative values allowed
        - Food quantities must be > 0
        - Calorie math must be correct (±5% tolerance)

        Args:
            data: Parsed data from Claude

        Returns:
            Validated and sanitized data

        Raises:
            ValueError: If data structure is invalid
        """
        if "foods" not in data or not isinstance(data["foods"], list):
            raise ValueError("Invalid data structure: 'foods' array required")

        validated_foods = []
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0

        for food in data["foods"]:
            # Ensure all required fields exist
            if not all(k in food for k in ["name", "quantity", "calories", "protein_g", "carbs_g", "fat_g"]):
                logger.warning(f"Skipping incomplete food item: {food.get('name', 'unknown')}")
                continue

            # CRITICAL: Clamp all nutrition values to >= 0
            calories = max(0, float(food["calories"]))
            protein_g = max(0, float(food["protein_g"]))
            carbs_g = max(0, float(food["carbs_g"]))
            fat_g = max(0, float(food["fat_g"]))
            quantity = max(0, float(food["quantity"]))

            # Skip if quantity is 0
            if quantity == 0:
                logger.warning(f"Skipping food with 0 quantity: {food['name']}")
                continue

            # Validate calorie calculation (±5% tolerance)
            calculated_calories = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
            tolerance = calculated_calories * 0.05

            if abs(calories - calculated_calories) > tolerance:
                logger.warning(
                    f"Calorie mismatch for {food['name']}: "
                    f"stated={calories}, calculated={calculated_calories}. "
                    f"Using calculated value."
                )
                calories = round(calculated_calories, 2)

            validated_food = {
                "name": str(food["name"]).strip(),
                "quantity": round(quantity, 2),
                "unit": str(food.get("unit", "g")),
                "calories": round(calories, 2),
                "protein_g": round(protein_g, 2),
                "carbs_g": round(carbs_g, 2),
                "fat_g": round(fat_g, 2)
            }

            validated_foods.append(validated_food)

            # Update totals
            total_calories += calories
            total_protein += protein_g
            total_carbs += carbs_g
            total_fat += fat_g

        return {
            "foods": validated_foods,
            "total_calories": round(total_calories, 2),
            "total_macros": {
                "protein": round(total_protein, 2),
                "carbs": round(total_carbs, 2),
                "fat": round(total_fat, 2)
            },
            "message": data.get("message", "Food logged successfully!")
        }

    def _validate_nutrition_data_v2(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced nutrition data validation using NutritionValidator (US-036).

        This replaces the old _validate_nutrition_data() with more comprehensive
        validation including:
        - Stricter range checks (max 5000 cal/food, max 2000g portion)
        - Better error reporting
        - Auto-correction with warnings
        - Water volume limits (10L max)

        Args:
            data: Parsed data from Claude

        Returns:
            Validated and corrected data

        Raises:
            ValueError: If data structure is critically invalid
        """
        validator = get_nutrition_validator()

        try:
            result = validator.validate_meal_data(data, auto_correct=True)

            # Log validation issues
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"Nutrition validation warning: {warning}")

            if not result.is_valid:
                error_msg = "; ".join(result.errors)
                logger.error(f"Nutrition validation failed: {error_msg}")
                raise ValueError(f"Invalid nutrition data: {error_msg}")

            # Log validation summary
            summary = validator.get_validation_summary()
            if summary["warning_count"] > 0:
                logger.info(f"Validation completed with {summary['warning_count']} warnings")

            return result.corrected_data

        except Exception as e:
            logger.error(f"Validation error: {e}")
            # Fallback to old validation method if new validator fails
            logger.warning("Falling back to legacy validation method")
            return self._validate_nutrition_data(data)


# Singleton instance
_claude_service: Optional[ClaudeService] = None


def get_claude_service() -> ClaudeService:
    """Get or create ClaudeService singleton instance."""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
