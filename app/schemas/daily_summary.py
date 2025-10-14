"""
Pydantic schemas for daily summary and nutrition tracking.

This module provides data models for:
- Daily nutrition summaries
- Macro progress tracking
- Meal type breakdowns
- Weekly trends
- End-of-day projections
- Calorie balance calculations
- Eating window analysis
"""

from datetime import date as date_type, time as time_type
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class MacroProgress(BaseModel):
    """Progress for a single macro nutrient."""
    consumed: Decimal = Field(..., ge=0, description="Amount consumed in grams")
    goal: Decimal = Field(..., ge=0, description="Target amount in grams")
    remaining: Decimal = Field(..., description="Amount remaining (can be negative)")
    percent: float = Field(..., ge=0, le=200, description="Percentage of goal achieved")
    status: str = Field(..., description="Status: on_track, under, over")

    class Config:
        json_schema_extra = {
            "example": {
                "consumed": 145.5,
                "goal": 165.0,
                "remaining": 19.5,
                "percent": 88.2,
                "status": "on_track"
            }
        }


class CalorieProgress(BaseModel):
    """Progress for daily calorie intake."""
    consumed: int = Field(..., ge=0, description="Calories consumed")
    goal: int = Field(..., ge=0, description="Calorie target")
    remaining: int = Field(..., description="Calories remaining (can be negative)")
    percent: float = Field(..., ge=0, le=200, description="Percentage of goal achieved")
    status: str = Field(..., description="Status: on_track, under, over")

    class Config:
        json_schema_extra = {
            "example": {
                "consumed": 1850,
                "goal": 2200,
                "remaining": 350,
                "percent": 84.1,
                "status": "on_track"
            }
        }


class MealTypeBreakdown(BaseModel):
    """Nutrition breakdown for a single meal type."""
    meal_type: str = Field(..., description="breakfast, lunch, dinner, or snack")
    calories: int = Field(..., ge=0, description="Total calories for this meal type")
    protein_g: Decimal = Field(..., ge=0, description="Total protein in grams")
    carbs_g: Decimal = Field(..., ge=0, description="Total carbs in grams")
    fat_g: Decimal = Field(..., ge=0, description="Total fat in grams")
    percent_of_daily: float = Field(..., ge=0, le=100, description="Percent of daily calories")
    meal_count: int = Field(..., ge=0, description="Number of meals of this type")

    class Config:
        json_schema_extra = {
            "example": {
                "meal_type": "breakfast",
                "calories": 450,
                "protein_g": 25.0,
                "carbs_g": 50.0,
                "fat_g": 15.0,
                "percent_of_daily": 24.3,
                "meal_count": 1
            }
        }


class CalorieBalance(BaseModel):
    """Calorie deficit or surplus calculation."""
    consumed: int = Field(..., ge=0, description="Total calories consumed")
    goal: int = Field(..., ge=0, description="Daily calorie goal")
    deficit: int = Field(..., description="Calorie deficit (positive) or surplus (negative)")
    deficit_percent: float = Field(..., description="Deficit as percentage of goal")
    weekly_impact: int = Field(..., description="Projected weekly calorie impact")
    weekly_weight_change: float = Field(..., description="Estimated weekly weight change in kg")

    class Config:
        json_schema_extra = {
            "example": {
                "consumed": 1850,
                "goal": 2200,
                "deficit": 350,
                "deficit_percent": 15.9,
                "weekly_impact": 2450,
                "weekly_weight_change": -0.35
            }
        }


class EatingWindow(BaseModel):
    """Analysis of eating window for intermittent fasting tracking."""
    first_meal_time: Optional[time_type] = Field(None, description="Time of first meal")
    last_meal_time: Optional[time_type] = Field(None, description="Time of last meal")
    eating_window_hours: Optional[float] = Field(None, ge=0, le=24, description="Hours of eating window")
    fasting_window_hours: Optional[float] = Field(None, ge=0, le=24, description="Hours of fasting window")
    is_intermittent_fasting: bool = Field(default=False, description="True if fasting >= 16 hours")

    class Config:
        json_schema_extra = {
            "example": {
                "first_meal_time": "07:30:00",
                "last_meal_time": "20:00:00",
                "eating_window_hours": 12.5,
                "fasting_window_hours": 11.5,
                "is_intermittent_fasting": False
            }
        }


class EndOfDayProjection(BaseModel):
    """Projection of final daily totals based on current progress."""
    current_time: time_type = Field(..., description="Time of projection")
    current_calories: int = Field(..., ge=0, description="Calories consumed so far")
    projected_total: int = Field(..., ge=0, description="Estimated final daily total")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    recommendation: str = Field(..., description="on_track, need_more, or slow_down")
    remaining_budget: int = Field(..., description="Calories remaining in budget")
    meals_remaining: List[str] = Field(default_factory=list, description="Meal types not yet logged")
    suggested_calories: int = Field(..., ge=0, description="Suggested calories for remaining meals")

    class Config:
        json_schema_extra = {
            "example": {
                "current_time": "16:00:00",
                "current_calories": 1300,
                "projected_total": 2100,
                "confidence": 0.75,
                "recommendation": "on_track",
                "remaining_budget": 900,
                "meals_remaining": ["dinner"],
                "suggested_calories": 800
            }
        }


class DailyTotals(BaseModel):
    """Total nutrition for the day."""
    date: date_type = Field(..., description="Date of summary")
    total_calories: int = Field(..., ge=0, description="Total calories consumed")
    total_protein: Decimal = Field(..., ge=0, description="Total protein in grams")
    total_carbs: Decimal = Field(..., ge=0, description="Total carbs in grams")
    total_fat: Decimal = Field(..., ge=0, description="Total fat in grams")
    protein_percent: float = Field(..., ge=0, le=100, description="Protein % of total calories")
    carbs_percent: float = Field(..., ge=0, le=100, description="Carbs % of total calories")
    fat_percent: float = Field(..., ge=0, le=100, description="Fat % of total calories")
    meal_count: int = Field(..., ge=0, description="Total number of meals logged")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-10-14",
                "total_calories": 1850,
                "total_protein": 145.5,
                "total_carbs": 180.0,
                "total_fat": 55.0,
                "protein_percent": 31.4,
                "carbs_percent": 38.9,
                "fat_percent": 26.8,
                "meal_count": 4
            }
        }


class DailySummaryResponse(BaseModel):
    """Complete daily nutrition summary with all metrics."""
    date: date_type = Field(..., description="Date of summary")
    totals: DailyTotals = Field(..., description="Daily nutrition totals")
    by_meal_type: List[MealTypeBreakdown] = Field(default_factory=list, description="Breakdown by meal type")
    calorie_progress: Optional[CalorieProgress] = Field(None, description="Calorie progress vs goal")
    protein_progress: Optional[MacroProgress] = Field(None, description="Protein progress vs goal")
    carbs_progress: Optional[MacroProgress] = Field(None, description="Carbs progress vs goal")
    fat_progress: Optional[MacroProgress] = Field(None, description="Fat progress vs goal")
    calorie_balance: Optional[CalorieBalance] = Field(None, description="Deficit/surplus calculation")
    eating_window: Optional[EatingWindow] = Field(None, description="Eating window analysis")
    projection: Optional[EndOfDayProjection] = Field(None, description="End-of-day projection")
    has_goals: bool = Field(default=False, description="True if user has set nutrition goals")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-10-14",
                "totals": {
                    "date": "2024-10-14",
                    "total_calories": 1850,
                    "total_protein": 145.5,
                    "total_carbs": 180.0,
                    "total_fat": 55.0,
                    "protein_percent": 31.4,
                    "carbs_percent": 38.9,
                    "fat_percent": 26.8,
                    "meal_count": 4
                },
                "by_meal_type": [
                    {
                        "meal_type": "breakfast",
                        "calories": 450,
                        "protein_g": 25.0,
                        "carbs_g": 50.0,
                        "fat_g": 15.0,
                        "percent_of_daily": 24.3,
                        "meal_count": 1
                    }
                ],
                "calorie_progress": {
                    "consumed": 1850,
                    "goal": 2200,
                    "remaining": 350,
                    "percent": 84.1,
                    "status": "on_track"
                },
                "has_goals": True
            }
        }


class DailyData(BaseModel):
    """Single day's data for weekly trends."""
    date: date_type = Field(..., description="Date")
    calories: int = Field(..., ge=0, description="Total calories")
    protein: Decimal = Field(..., ge=0, description="Total protein in grams")
    carbs: Decimal = Field(..., ge=0, description="Total carbs in grams")
    fat: Decimal = Field(..., ge=0, description="Total fat in grams")
    meal_count: int = Field(..., ge=0, description="Number of meals")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-10-14",
                "calories": 2150,
                "protein": 158.0,
                "carbs": 235.0,
                "fat": 68.0,
                "meal_count": 4
            }
        }


class WeeklyAverages(BaseModel):
    """Average nutrition values for the week."""
    calories: float = Field(..., ge=0, description="Average daily calories")
    protein: float = Field(..., ge=0, description="Average daily protein in grams")
    carbs: float = Field(..., ge=0, description="Average daily carbs in grams")
    fat: float = Field(..., ge=0, description="Average daily fat in grams")
    meal_count: float = Field(..., ge=0, description="Average meals per day")

    class Config:
        json_schema_extra = {
            "example": {
                "calories": 2150.0,
                "protein": 158.5,
                "carbs": 235.0,
                "fat": 68.0,
                "meal_count": 4.2
            }
        }


class WeeklyTrends(BaseModel):
    """Weekly nutrition trends analysis."""
    date_range: List[date_type] = Field(..., min_length=2, max_length=2, description="[start_date, end_date]")
    days_with_data: int = Field(..., ge=0, le=7, description="Number of days with logged meals")
    daily_averages: WeeklyAverages = Field(..., description="Average values across the week")
    daily_data: List[DailyData] = Field(default_factory=list, description="Data for each day")
    trend: str = Field(..., description="increasing, decreasing, or stable")
    variance: float = Field(..., ge=0, description="Variance in calories (% coefficient of variation)")
    consistency_score: float = Field(..., ge=0, le=1, description="How consistent the user is (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "date_range": ["2024-10-08", "2024-10-14"],
                "days_with_data": 7,
                "daily_averages": {
                    "calories": 2150.0,
                    "protein": 158.5,
                    "carbs": 235.0,
                    "fat": 68.0,
                    "meal_count": 4.2
                },
                "daily_data": [],
                "trend": "stable",
                "variance": 8.5,
                "consistency_score": 0.92
            }
        }


class ComparisonDay(BaseModel):
    """Single day's data for comparison."""
    date: date_type = Field(..., description="Date")
    calories: int = Field(..., ge=0, description="Total calories")
    protein: Decimal = Field(..., ge=0, description="Total protein")
    carbs: Decimal = Field(..., ge=0, description="Total carbs")
    fat: Decimal = Field(..., ge=0, description="Total fat")
    meal_count: int = Field(..., ge=0, description="Number of meals")


class ComparisonDifference(BaseModel):
    """Difference between two days."""
    calories: int = Field(..., description="Calorie difference")
    protein: Decimal = Field(..., description="Protein difference")
    carbs: Decimal = Field(..., description="Carbs difference")
    fat: Decimal = Field(..., description="Fat difference")
    calories_percent: float = Field(..., description="Percent change in calories")


class ComparisonResult(BaseModel):
    """Comparison between multiple days."""
    days: List[ComparisonDay] = Field(..., description="Days being compared")
    difference: Optional[ComparisonDifference] = Field(None, description="Difference (only for 2 days)")
    analysis: str = Field(..., description="Text analysis of the comparison")

    class Config:
        json_schema_extra = {
            "example": {
                "days": [
                    {
                        "date": "2024-10-13",
                        "calories": 2300,
                        "protein": 165.0,
                        "carbs": 250.0,
                        "fat": 70.0,
                        "meal_count": 4
                    },
                    {
                        "date": "2024-10-14",
                        "calories": 1850,
                        "protein": 145.0,
                        "carbs": 180.0,
                        "fat": 55.0,
                        "meal_count": 4
                    }
                ],
                "difference": {
                    "calories": -450,
                    "protein": -20.0,
                    "carbs": -70.0,
                    "fat": -15.0,
                    "calories_percent": -19.6
                },
                "analysis": "You consumed 450 fewer calories today (-19.6%). Good deficit for weight loss."
            }
        }
