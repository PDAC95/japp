"""
Food search service with intelligent prioritization.

Implements food search across system foods, user foods, and favorites
with relevance scoring and filtering.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.core.supabase import get_supabase_client
from app.schemas.food import (
    FoodSearchFilters,
    FoodSearchResultItem,
)
import logging

logger = logging.getLogger(__name__)


class FoodSearchService:
    """Service for searching and managing foods."""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def search_foods(
        self,
        user_id: str,
        query: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[FoodSearchFilters] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for foods with intelligent prioritization.

        Priority order:
        1. User's custom foods (exact match)
        2. User's favorite foods
        3. System foods (exact match)
        4. Partial matches (user foods)
        5. Partial matches (system foods)
        6. Category matches

        Args:
            user_id: User UUID
            query: Search query string
            page: Page number (starts at 1)
            page_size: Items per page
            filters: Optional search filters

        Returns:
            Tuple of (results list, total count)
        """
        try:
            # Calculate offset for pagination
            offset = (page - 1) * page_size

            # Build filter conditions
            filter_conditions = self._build_filter_conditions(filters)

            # Search strategy:
            # 1. Get user's custom foods with search
            # 2. Get system foods with search
            # 3. Get user's favorites
            # 4. Merge and prioritize results
            # 5. Apply filters
            # 6. Calculate relevance scores
            # 7. Sort by score + paginate

            results = []

            # Step 1: Search user's custom foods
            if not filters or not filters.only_user_foods:
                user_foods = await self._search_user_foods(
                    user_id, query, filter_conditions
                )
                results.extend(user_foods)

            # Step 2: Search system foods (only if not user_foods_only)
            if not filters or not filters.only_user_foods:
                system_foods = await self._search_system_foods(
                    query, filter_conditions
                )
                results.extend(system_foods)

            # Step 3: Get user's favorites and mark them
            favorites = await self._get_user_favorites(user_id)
            favorite_ids = {fav["food_id"] or fav["user_food_id"] for fav in favorites}
            favorite_use_counts = {
                fav["food_id"]
                or fav["user_food_id"]: fav["use_count"]
                for fav in favorites
            }

            # Mark favorites and add use_count
            for result in results:
                if result["id"] in favorite_ids:
                    result["is_favorite"] = True
                    result["use_count"] = favorite_use_counts[result["id"]]
                    # Boost relevance for favorites
                    result["relevance_score"] = min(
                        1.0, result.get("relevance_score", 0.5) + 0.3
                    )
                else:
                    result["is_favorite"] = False
                    result["use_count"] = None

            # Step 4: Calculate relevance scores
            results = self._calculate_relevance(results, query)

            # Step 5: Remove duplicates (prefer user foods over system)
            results = self._remove_duplicates(results)

            # Step 6: Sort by relevance score (highest first)
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Get total count before pagination
            total_count = len(results)

            # Step 7: Apply pagination
            paginated_results = results[offset : offset + page_size]

            return paginated_results, total_count

        except Exception as e:
            logger.error(f"Food search error: {str(e)}")
            raise

    async def _search_user_foods(
        self, user_id: str, query: str, filter_conditions: Dict
    ) -> List[Dict[str, Any]]:
        """Search user's custom foods."""
        try:
            # Build query
            query_builder = (
                self.supabase.table("user_foods")
                .select("*")
                .eq("user_id", user_id)
                .ilike("name", f"%{query}%")  # Case-insensitive LIKE
            )

            # Apply filters
            query_builder = self._apply_filters(query_builder, filter_conditions)

            # Execute query
            response = query_builder.execute()

            # Format results
            results = []
            for food in response.data:
                results.append(
                    {
                        "id": food["id"],
                        "source": "user",
                        "name": food["name"],
                        "name_en": None,
                        "category": food["category"],
                        "brand_name": None,  # TODO: Join brands
                        "calories": float(food["calories"]),
                        "protein_g": float(food["protein_g"]),
                        "carbs_g": float(food["carbs_g"]),
                        "fat_g": float(food["fat_g"]),
                        "serving_size_g": float(food["serving_size_g"]),
                        "serving_size_description": food.get(
                            "serving_size_description"
                        ),
                        "relevance_score": 0.8,  # User foods get high base score
                    }
                )

            return results

        except Exception as e:
            logger.error(f"User foods search error: {str(e)}")
            return []

    async def _search_system_foods(
        self, query: str, filter_conditions: Dict
    ) -> List[Dict[str, Any]]:
        """Search system foods database."""
        try:
            # Build query
            query_builder = (
                self.supabase.table("foods")
                .select("*, food_brands(name)")
                .eq("verified", True)  # Only verified foods
                .or_(f"name.ilike.%{query}%,name_en.ilike.%{query}%")
            )

            # Apply filters
            query_builder = self._apply_filters(query_builder, filter_conditions)

            # Execute query
            response = query_builder.execute()

            # Format results
            results = []
            for food in response.data:
                brand_name = None
                if food.get("food_brands"):
                    brand_name = food["food_brands"].get("name")

                results.append(
                    {
                        "id": food["id"],
                        "source": "system",
                        "name": food["name"],
                        "name_en": food.get("name_en"),
                        "category": food["category"],
                        "brand_name": brand_name,
                        "calories": float(food["calories"]),
                        "protein_g": float(food["protein_g"]),
                        "carbs_g": float(food["carbs_g"]),
                        "fat_g": float(food["fat_g"]),
                        "serving_size_g": float(food["serving_size_g"]),
                        "serving_size_description": food.get(
                            "serving_size_description"
                        ),
                        "relevance_score": 0.6,  # System foods get medium base score
                    }
                )

            return results

        except Exception as e:
            logger.error(f"System foods search error: {str(e)}")
            return []

    async def _get_user_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's favorite foods."""
        try:
            response = (
                self.supabase.table("food_favorites")
                .select("food_id, user_food_id, use_count")
                .eq("user_id", user_id)
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(f"Favorites fetch error: {str(e)}")
            return []

    def _build_filter_conditions(
        self, filters: Optional[FoodSearchFilters]
    ) -> Dict[str, Any]:
        """Build filter conditions dictionary."""
        if not filters:
            return {}

        conditions = {}

        if filters.category:
            conditions["category"] = filters.category

        if filters.brand_id:
            conditions["brand_id"] = filters.brand_id

        if filters.min_calories is not None:
            conditions["min_calories"] = float(filters.min_calories)

        if filters.max_calories is not None:
            conditions["max_calories"] = float(filters.max_calories)

        if filters.is_vegetarian is not None:
            conditions["is_vegetarian"] = filters.is_vegetarian

        if filters.is_vegan is not None:
            conditions["is_vegan"] = filters.is_vegan

        if filters.is_gluten_free is not None:
            conditions["is_gluten_free"] = filters.is_gluten_free

        return conditions

    def _apply_filters(self, query_builder, filter_conditions: Dict):
        """Apply filter conditions to Supabase query builder."""
        if "category" in filter_conditions:
            query_builder = query_builder.eq("category", filter_conditions["category"])

        if "brand_id" in filter_conditions:
            query_builder = query_builder.eq("brand_id", filter_conditions["brand_id"])

        if "min_calories" in filter_conditions:
            query_builder = query_builder.gte(
                "calories", filter_conditions["min_calories"]
            )

        if "max_calories" in filter_conditions:
            query_builder = query_builder.lte(
                "calories", filter_conditions["max_calories"]
            )

        if "is_vegetarian" in filter_conditions:
            query_builder = query_builder.eq(
                "is_vegetarian", filter_conditions["is_vegetarian"]
            )

        if "is_vegan" in filter_conditions:
            query_builder = query_builder.eq(
                "is_vegan", filter_conditions["is_vegan"]
            )

        if "is_gluten_free" in filter_conditions:
            query_builder = query_builder.eq(
                "is_gluten_free", filter_conditions["is_gluten_free"]
            )

        return query_builder

    def _calculate_relevance(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Calculate relevance scores based on query match."""
        query_lower = query.lower()

        for result in results:
            name_lower = result["name"].lower()
            base_score = result.get("relevance_score", 0.5)

            # Exact match
            if name_lower == query_lower:
                result["relevance_score"] = min(1.0, base_score + 0.4)

            # Starts with query
            elif name_lower.startswith(query_lower):
                result["relevance_score"] = min(1.0, base_score + 0.3)

            # Contains query
            elif query_lower in name_lower:
                result["relevance_score"] = min(1.0, base_score + 0.2)

            # Partial word match
            elif any(word.startswith(query_lower) for word in name_lower.split()):
                result["relevance_score"] = min(1.0, base_score + 0.1)

        return results

    def _remove_duplicates(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate foods, preferring user foods over system foods."""
        seen = {}
        unique_results = []

        for result in results:
            # Use lowercase name as key
            key = result["name"].lower()

            if key not in seen:
                seen[key] = result
                unique_results.append(result)
            else:
                # If current is user food and existing is system, replace
                existing = seen[key]
                if result["source"] == "user" and existing["source"] == "system":
                    unique_results.remove(existing)
                    seen[key] = result
                    unique_results.append(result)

        return unique_results

    async def get_food_by_id(
        self, food_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get food by ID (system or user food)."""
        try:
            # Try system foods first
            response = (
                self.supabase.table("foods")
                .select("*, food_brands(name)")
                .eq("id", food_id)
                .eq("verified", True)
                .maybe_single()
                .execute()
            )

            if response.data:
                food = response.data
                return {
                    "id": food["id"],
                    "source": "system",
                    "name": food["name"],
                    "name_en": food.get("name_en"),
                    "category": food["category"],
                    "brand_name": food.get("food_brands", {}).get("name"),
                    "calories": float(food["calories"]),
                    "protein_g": float(food["protein_g"]),
                    "carbs_g": float(food["carbs_g"]),
                    "fat_g": float(food["fat_g"]),
                    "fiber_g": float(food.get("fiber_g", 0)),
                    "sugar_g": float(food.get("sugar_g", 0)),
                    "sodium_mg": float(food.get("sodium_mg", 0)),
                    "serving_size_g": float(food["serving_size_g"]),
                    "serving_size_description": food.get("serving_size_description"),
                }

            # Try user foods if not found in system
            if user_id:
                response = (
                    self.supabase.table("user_foods")
                    .select("*")
                    .eq("id", food_id)
                    .eq("user_id", user_id)
                    .maybe_single()
                    .execute()
                )

                if response.data:
                    food = response.data
                    return {
                        "id": food["id"],
                        "source": "user",
                        "name": food["name"],
                        "category": food["category"],
                        "calories": float(food["calories"]),
                        "protein_g": float(food["protein_g"]),
                        "carbs_g": float(food["carbs_g"]),
                        "fat_g": float(food["fat_g"]),
                        "fiber_g": float(food.get("fiber_g", 0)),
                        "sugar_g": float(food.get("sugar_g", 0)),
                        "sodium_mg": float(food.get("sodium_mg", 0)),
                        "serving_size_g": float(food["serving_size_g"]),
                        "serving_size_description": food.get(
                            "serving_size_description"
                        ),
                    }

            return None

        except Exception as e:
            logger.error(f"Get food by ID error: {str(e)}")
            return None
