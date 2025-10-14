"""
Service for calculating daily nutrition summaries and trends.

This service provides:
- Daily nutrition totals and breakdowns
- Progress tracking against user goals
- Weekly trend analysis
- End-of-day projections
- Eating window calculations
- Multi-day comparisons
"""

from datetime import date, datetime, timedelta, time as time_type
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import statistics

from supabase import Client

from app.schemas.daily_summary import (
    DailySummaryResponse,
    DailyTotals,
    MealTypeBreakdown,
    CalorieProgress,
    MacroProgress,
    CalorieBalance,
    EatingWindow,
    EndOfDayProjection,
    WeeklyTrends,
    WeeklyAverages,
    DailyData,
    ComparisonResult,
    ComparisonDay,
    ComparisonDifference
)


# Status thresholds
STATUS_UNDER_THRESHOLD = 0.80  # Below 80% is "under"
STATUS_OVER_THRESHOLD = 1.15   # Above 115% is "over"

# Projection confidence factors
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.70

# Trend analysis
TREND_THRESHOLD = 0.05  # 5% change to be considered increasing/decreasing

# Eating window
INTERMITTENT_FASTING_HOURS = 16.0


class DailySummaryService:
    """Service for daily nutrition summary calculations."""

    def __init__(self, supabase: Client):
        """
        Initialize the service.

        Args:
            supabase: Supabase client for database access
        """
        self.supabase = supabase

    async def get_daily_summary(
        self,
        user_id: UUID,
        target_date: date,
        include_projection: bool = True
    ) -> DailySummaryResponse:
        """
        Get complete daily nutrition summary with all metrics.

        Args:
            user_id: User ID
            target_date: Date to get summary for
            include_projection: Whether to include end-of-day projection

        Returns:
            Complete daily summary with totals, breakdowns, and progress
        """
        # Get all meal entries for the day
        entries = await self._get_meal_entries_for_date(user_id, target_date)

        # Calculate daily totals
        totals = self._calculate_daily_totals(target_date, entries)

        # Calculate breakdown by meal type
        by_meal_type = self._calculate_meal_type_breakdown(entries, totals.total_calories)

        # Get user goals
        user_goals = await self._get_user_goals(user_id)
        has_goals = user_goals is not None

        # Calculate progress metrics if goals exist
        calorie_progress = None
        protein_progress = None
        carbs_progress = None
        fat_progress = None
        calorie_balance = None

        if has_goals:
            calorie_progress = self._calculate_calorie_progress(
                totals.total_calories,
                user_goals["daily_calories"]
            )
            protein_progress = self._calculate_macro_progress(
                totals.total_protein,
                Decimal(str(user_goals["protein_g"]))
            )
            carbs_progress = self._calculate_macro_progress(
                totals.total_carbs,
                Decimal(str(user_goals["carbs_g"]))
            )
            fat_progress = self._calculate_macro_progress(
                totals.total_fat,
                Decimal(str(user_goals["fat_g"]))
            )
            calorie_balance = self._calculate_calorie_balance(
                totals.total_calories,
                user_goals["daily_calories"]
            )

        # Calculate eating window
        eating_window = self._calculate_eating_window(entries)

        # Calculate projection if requested and not end of day
        projection = None
        if include_projection and self._should_project(target_date):
            projection = await self._calculate_projection(
                user_id,
                target_date,
                totals.total_calories,
                user_goals["daily_calories"] if has_goals else 2000,
                by_meal_type
            )

        return DailySummaryResponse(
            date=target_date,
            totals=totals,
            by_meal_type=by_meal_type,
            calorie_progress=calorie_progress,
            protein_progress=protein_progress,
            carbs_progress=carbs_progress,
            fat_progress=fat_progress,
            calorie_balance=calorie_balance,
            eating_window=eating_window,
            projection=projection,
            has_goals=has_goals
        )

    async def get_weekly_trends(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> WeeklyTrends:
        """
        Calculate weekly nutrition trends.

        Args:
            user_id: User ID
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Weekly trends with averages and daily data
        """
        # Get data for each day in range
        daily_data: List[DailyData] = []
        current_date = start_date

        while current_date <= end_date:
            entries = await self._get_meal_entries_for_date(user_id, current_date)

            if entries:  # Only include days with data
                totals = self._calculate_daily_totals(current_date, entries)
                daily_data.append(DailyData(
                    date=current_date,
                    calories=totals.total_calories,
                    protein=totals.total_protein,
                    carbs=totals.total_carbs,
                    fat=totals.total_fat,
                    meal_count=totals.meal_count
                ))

            current_date += timedelta(days=1)

        # Calculate averages
        if daily_data:
            avg_calories = sum(d.calories for d in daily_data) / len(daily_data)
            avg_protein = sum(d.protein for d in daily_data) / len(daily_data)
            avg_carbs = sum(d.carbs for d in daily_data) / len(daily_data)
            avg_fat = sum(d.fat for d in daily_data) / len(daily_data)
            avg_meals = sum(d.meal_count for d in daily_data) / len(daily_data)
        else:
            avg_calories = avg_protein = avg_carbs = avg_fat = avg_meals = 0

        averages = WeeklyAverages(
            calories=round(avg_calories, 1),
            protein=round(float(avg_protein), 1),
            carbs=round(float(avg_carbs), 1),
            fat=round(float(avg_fat), 1),
            meal_count=round(avg_meals, 1)
        )

        # Analyze trend
        trend = self._analyze_trend(daily_data)
        variance = self._calculate_variance(daily_data)
        consistency = self._calculate_consistency_score(variance)

        return WeeklyTrends(
            date_range=[start_date, end_date],
            days_with_data=len(daily_data),
            daily_averages=averages,
            daily_data=daily_data,
            trend=trend,
            variance=round(variance, 2),
            consistency_score=round(consistency, 2)
        )

    async def compare_days(
        self,
        user_id: UUID,
        dates: List[date]
    ) -> ComparisonResult:
        """
        Compare nutrition across multiple days.

        Args:
            user_id: User ID
            dates: List of dates to compare

        Returns:
            Comparison result with analysis
        """
        comparison_days: List[ComparisonDay] = []

        for target_date in dates:
            entries = await self._get_meal_entries_for_date(user_id, target_date)
            totals = self._calculate_daily_totals(target_date, entries)

            comparison_days.append(ComparisonDay(
                date=target_date,
                calories=totals.total_calories,
                protein=totals.total_protein,
                carbs=totals.total_carbs,
                fat=totals.total_fat,
                meal_count=totals.meal_count
            ))

        # Calculate difference if exactly 2 days
        difference = None
        if len(comparison_days) == 2:
            day1, day2 = comparison_days[0], comparison_days[1]
            cal_diff = day2.calories - day1.calories
            cal_percent = (cal_diff / day1.calories * 100) if day1.calories > 0 else 0

            difference = ComparisonDifference(
                calories=cal_diff,
                protein=day2.protein - day1.protein,
                carbs=day2.carbs - day1.carbs,
                fat=day2.fat - day1.fat,
                calories_percent=round(cal_percent, 1)
            )

        # Generate analysis
        analysis = self._generate_comparison_analysis(comparison_days, difference)

        return ComparisonResult(
            days=comparison_days,
            difference=difference,
            analysis=analysis
        )

    # ==================== Private Helper Methods ====================

    async def _get_meal_entries_for_date(
        self,
        user_id: UUID,
        target_date: date
    ) -> List[Dict[str, Any]]:
        """Get all meal entries for a specific date."""
        response = self.supabase.table("meal_entries") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .eq("date", str(target_date)) \
            .order("time", desc=False) \
            .execute()

        return response.data if response.data else []

    async def _get_user_goals(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user nutrition goals from profiles."""
        try:
            response = self.supabase.table("profiles") \
                .select("daily_calories, protein_g, carbs_g, fat_g") \
                .eq("user_id", str(user_id)) \
                .execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception:
            # Goals not set yet, return None
            pass
        return None

    def _calculate_daily_totals(
        self,
        target_date: date,
        entries: List[Dict[str, Any]]
    ) -> DailyTotals:
        """Calculate total nutrition for the day."""
        if not entries:
            return DailyTotals(
                date=target_date,
                total_calories=0,
                total_protein=Decimal("0"),
                total_carbs=Decimal("0"),
                total_fat=Decimal("0"),
                protein_percent=0.0,
                carbs_percent=0.0,
                fat_percent=0.0,
                meal_count=0
            )

        total_calories = sum(e["calories"] for e in entries)
        total_protein = sum(Decimal(str(e["protein_g"])) for e in entries)
        total_carbs = sum(Decimal(str(e["carbs_g"])) for e in entries)
        total_fat = sum(Decimal(str(e["fat_g"])) for e in entries)

        # Calculate macro percentages
        if total_calories > 0:
            protein_percent = (float(total_protein) * 4 / total_calories) * 100
            carbs_percent = (float(total_carbs) * 4 / total_calories) * 100
            fat_percent = (float(total_fat) * 9 / total_calories) * 100
        else:
            protein_percent = carbs_percent = fat_percent = 0.0

        return DailyTotals(
            date=target_date,
            total_calories=total_calories,
            total_protein=round(total_protein, 1),
            total_carbs=round(total_carbs, 1),
            total_fat=round(total_fat, 1),
            protein_percent=round(protein_percent, 1),
            carbs_percent=round(carbs_percent, 1),
            fat_percent=round(fat_percent, 1),
            meal_count=len(entries)
        )

    def _calculate_meal_type_breakdown(
        self,
        entries: List[Dict[str, Any]],
        total_calories: int
    ) -> List[MealTypeBreakdown]:
        """Calculate nutrition breakdown by meal type."""
        # Group by meal type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for entry in entries:
            meal_type = entry["meal_type"]
            if meal_type not in by_type:
                by_type[meal_type] = []
            by_type[meal_type].append(entry)

        # Calculate totals for each type
        breakdowns: List[MealTypeBreakdown] = []
        for meal_type, type_entries in by_type.items():
            type_calories = sum(e["calories"] for e in type_entries)
            type_protein = sum(Decimal(str(e["protein_g"])) for e in type_entries)
            type_carbs = sum(Decimal(str(e["carbs_g"])) for e in type_entries)
            type_fat = sum(Decimal(str(e["fat_g"])) for e in type_entries)

            percent = (type_calories / total_calories * 100) if total_calories > 0 else 0.0

            breakdowns.append(MealTypeBreakdown(
                meal_type=meal_type,
                calories=type_calories,
                protein_g=round(type_protein, 1),
                carbs_g=round(type_carbs, 1),
                fat_g=round(type_fat, 1),
                percent_of_daily=round(percent, 1),
                meal_count=len(type_entries)
            ))

        # Sort by standard meal order
        meal_order = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}
        breakdowns.sort(key=lambda x: meal_order.get(x.meal_type, 99))

        return breakdowns

    def _calculate_calorie_progress(
        self,
        consumed: int,
        goal: int
    ) -> CalorieProgress:
        """Calculate calorie progress against goal."""
        remaining = goal - consumed
        percent = (consumed / goal * 100) if goal > 0 else 0

        # Determine status
        if percent < STATUS_UNDER_THRESHOLD * 100:
            status = "under"
        elif percent > STATUS_OVER_THRESHOLD * 100:
            status = "over"
        else:
            status = "on_track"

        return CalorieProgress(
            consumed=consumed,
            goal=goal,
            remaining=remaining,
            percent=round(percent, 1),
            status=status
        )

    def _calculate_macro_progress(
        self,
        consumed: Decimal,
        goal: Decimal
    ) -> MacroProgress:
        """Calculate macro progress against goal."""
        remaining = goal - consumed
        percent = (float(consumed) / float(goal) * 100) if goal > 0 else 0

        # Determine status
        if percent < STATUS_UNDER_THRESHOLD * 100:
            status = "under"
        elif percent > STATUS_OVER_THRESHOLD * 100:
            status = "over"
        else:
            status = "on_track"

        return MacroProgress(
            consumed=round(consumed, 1),
            goal=round(goal, 1),
            remaining=round(remaining, 1),
            percent=round(percent, 1),
            status=status
        )

    def _calculate_calorie_balance(
        self,
        consumed: int,
        goal: int
    ) -> CalorieBalance:
        """Calculate calorie deficit or surplus."""
        deficit = goal - consumed  # Positive = deficit, negative = surplus
        deficit_percent = (deficit / goal * 100) if goal > 0 else 0
        weekly_impact = deficit * 7

        # 7700 cal = 1 kg (approximate)
        weekly_weight_change = weekly_impact / 7700

        return CalorieBalance(
            consumed=consumed,
            goal=goal,
            deficit=deficit,
            deficit_percent=round(deficit_percent, 1),
            weekly_impact=weekly_impact,
            weekly_weight_change=round(weekly_weight_change, 2)
        )

    def _calculate_eating_window(
        self,
        entries: List[Dict[str, Any]]
    ) -> Optional[EatingWindow]:
        """Calculate eating window for intermittent fasting tracking."""
        if not entries:
            return EatingWindow(
                first_meal_time=None,
                last_meal_time=None,
                eating_window_hours=None,
                fasting_window_hours=None,
                is_intermittent_fasting=False
            )

        # Parse times
        times = []
        for entry in entries:
            time_str = entry["time"]
            if isinstance(time_str, str):
                time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
            else:
                time_obj = time_str
            times.append(time_obj)

        first_meal = min(times)
        last_meal = max(times)

        # Calculate eating window in hours
        first_minutes = first_meal.hour * 60 + first_meal.minute
        last_minutes = last_meal.hour * 60 + last_meal.minute
        eating_window_minutes = last_minutes - first_minutes
        eating_window_hours = eating_window_minutes / 60
        fasting_window_hours = 24 - eating_window_hours

        is_if = fasting_window_hours >= INTERMITTENT_FASTING_HOURS

        return EatingWindow(
            first_meal_time=first_meal,
            last_meal_time=last_meal,
            eating_window_hours=round(eating_window_hours, 1),
            fasting_window_hours=round(fasting_window_hours, 1),
            is_intermittent_fasting=is_if
        )

    def _should_project(self, target_date: date) -> bool:
        """Determine if we should project end-of-day totals."""
        today = date.today()
        if target_date < today:
            return False  # Past days don't need projection
        if target_date > today:
            return False  # Future days can't be projected

        # Check if it's before 11 PM (reasonable cutoff)
        now = datetime.now()
        if now.hour >= 23:
            return False  # Too late, day is essentially done

        return True

    async def _calculate_projection(
        self,
        user_id: UUID,
        target_date: date,
        current_calories: int,
        goal_calories: int,
        by_meal_type: List[MealTypeBreakdown]
    ) -> EndOfDayProjection:
        """Calculate end-of-day projection based on current progress."""
        current_time = datetime.now().time()

        # Determine which meals are already logged
        logged_types = set(b.meal_type for b in by_meal_type)
        all_types = {"breakfast", "lunch", "dinner", "snack"}
        meals_remaining = list(all_types - logged_types)

        # Simple projection: assume remaining meals proportional to goal
        remaining_budget = goal_calories - current_calories

        # Confidence based on time of day and meals logged
        hour = current_time.hour
        confidence = 0.5  # Base confidence

        if hour >= 20:  # Evening, probably done eating
            confidence = 0.9
        elif hour >= 16:  # Afternoon
            confidence = 0.75
        elif hour >= 12:  # Midday
            confidence = 0.6

        # Adjust confidence based on meals logged
        if len(logged_types) >= 3:
            confidence += 0.1

        confidence = min(confidence, 1.0)

        # Project final total
        if len(meals_remaining) > 0:
            avg_remaining_meal = remaining_budget / len(meals_remaining)
            projected_total = current_calories + int(avg_remaining_meal * len(meals_remaining))
        else:
            projected_total = current_calories

        # Determine recommendation
        progress_percent = current_calories / goal_calories if goal_calories > 0 else 0

        if progress_percent < 0.70:
            recommendation = "need_more"
        elif progress_percent > 1.10:
            recommendation = "slow_down"
        else:
            recommendation = "on_track"

        # Suggested calories for remaining meals
        suggested = max(0, remaining_budget)

        return EndOfDayProjection(
            current_time=current_time,
            current_calories=current_calories,
            projected_total=projected_total,
            confidence=round(confidence, 2),
            recommendation=recommendation,
            remaining_budget=remaining_budget,
            meals_remaining=meals_remaining,
            suggested_calories=suggested
        )

    def _analyze_trend(self, daily_data: List[DailyData]) -> str:
        """Analyze if calories are increasing, decreasing, or stable."""
        if len(daily_data) < 2:
            return "stable"

        # Calculate trend using first half vs second half averages
        mid_point = len(daily_data) // 2
        first_half_avg = sum(d.calories for d in daily_data[:mid_point]) / mid_point
        second_half_avg = sum(d.calories for d in daily_data[mid_point:]) / (len(daily_data) - mid_point)

        change_percent = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0

        if change_percent > TREND_THRESHOLD:
            return "increasing"
        elif change_percent < -TREND_THRESHOLD:
            return "decreasing"
        else:
            return "stable"

    def _calculate_variance(self, daily_data: List[DailyData]) -> float:
        """Calculate variance in calories (coefficient of variation)."""
        if len(daily_data) < 2:
            return 0.0

        calories = [d.calories for d in daily_data]
        mean = statistics.mean(calories)
        stdev = statistics.stdev(calories)

        # Coefficient of variation (CV) = (stdev / mean) * 100
        cv = (stdev / mean * 100) if mean > 0 else 0
        return cv

    def _calculate_consistency_score(self, variance: float) -> float:
        """
        Calculate consistency score (0-1) based on variance.
        Lower variance = higher consistency.
        """
        # Variance of 0% = perfect consistency (1.0)
        # Variance of 20% = moderate consistency (0.5)
        # Variance of 40%+ = low consistency (0.0)

        if variance <= 0:
            return 1.0
        elif variance >= 40:
            return 0.0
        else:
            # Linear interpolation
            return 1.0 - (variance / 40)

    def _generate_comparison_analysis(
        self,
        days: List[ComparisonDay],
        difference: Optional[ComparisonDifference]
    ) -> str:
        """Generate text analysis of day comparison."""
        if len(days) < 2:
            return "Need at least 2 days to compare."

        if difference and len(days) == 2:
            day1, day2 = days[0], days[1]
            cal_change = difference.calories
            percent_change = difference.calories_percent

            if abs(percent_change) < 5:
                return f"Very similar intake on both days (~{abs(cal_change)} cal difference)."
            elif cal_change > 0:
                return f"You consumed {cal_change} more calories on {day2.date} (+{percent_change}%)."
            else:
                return f"You consumed {abs(cal_change)} fewer calories on {day2.date} ({percent_change}%)."
        else:
            avg_calories = sum(d.calories for d in days) / len(days)
            min_day = min(days, key=lambda d: d.calories)
            max_day = max(days, key=lambda d: d.calories)

            return (
                f"Average across {len(days)} days: {int(avg_calories)} cal. "
                f"Range: {min_day.calories} ({min_day.date}) to {max_day.calories} ({max_day.date})."
            )


def get_daily_summary_service(supabase: Client) -> DailySummaryService:
    """Dependency injection for DailySummaryService."""
    return DailySummaryService(supabase)
