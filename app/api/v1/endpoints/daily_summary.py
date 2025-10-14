"""
REST API endpoints for daily nutrition summaries.

This module provides endpoints for:
- Daily nutrition summaries
- Weekly trend analysis
- Day-to-day comparisons
- Real-time projections
"""

from datetime import date, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.daily_summary import (
    DailySummaryResponse,
    WeeklyTrends,
    ComparisonResult
)
from app.services.daily_summary_service import DailySummaryService
from app.core.supabase import get_supabase_client


router = APIRouter(prefix="/daily-summary", tags=["Daily Summary"])


# Dependency to get current user ID
async def get_current_user_id() -> UUID:
    """
    Get current authenticated user ID.

    In production, this would extract user_id from JWT token.
    For now, using a placeholder for testing.

    TODO: Implement proper auth middleware with Supabase JWT validation
    """
    # Placeholder - in production, extract from Authorization header
    return UUID("00000000-0000-0000-0000-000000000000")


# Dependency to get daily summary service
def get_daily_summary_service(supabase=Depends(get_supabase_client)) -> DailySummaryService:
    """Get DailySummaryService instance."""
    return DailySummaryService(supabase)


@router.get("/{target_date}", response_model=DailySummaryResponse)
async def get_daily_summary(
    target_date: date,
    include_projection: bool = Query(True, description="Include end-of-day projection"),
    user_id: UUID = Depends(get_current_user_id),
    service: DailySummaryService = Depends(get_daily_summary_service)
):
    """
    Get complete daily nutrition summary.

    Returns:
    - Daily totals (calories, protein, carbs, fat, percentages)
    - Breakdown by meal type (breakfast, lunch, dinner, snack)
    - Progress vs user goals (if goals are set)
    - Calorie balance (deficit/surplus)
    - Eating window analysis (for intermittent fasting)
    - End-of-day projection (if today and before 11 PM)

    **Example Response:**
    ```json
    {
      "date": "2024-10-14",
      "totals": {
        "total_calories": 1850,
        "total_protein": 145.5,
        "protein_percent": 31.4,
        ...
      },
      "by_meal_type": [
        {
          "meal_type": "breakfast",
          "calories": 450,
          "percent_of_daily": 24.3,
          ...
        }
      ],
      "calorie_progress": {
        "consumed": 1850,
        "goal": 2200,
        "remaining": 350,
        "percent": 84.1,
        "status": "on_track"
      },
      "eating_window": {
        "first_meal_time": "07:30:00",
        "last_meal_time": "20:00:00",
        "eating_window_hours": 12.5,
        "is_intermittent_fasting": false
      }
    }
    ```
    """
    try:
        summary = await service.get_daily_summary(
            user_id=user_id,
            target_date=target_date,
            include_projection=include_projection
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating daily summary: {str(e)}"
        )


@router.get("/weekly-trends/range", response_model=WeeklyTrends)
async def get_weekly_trends(
    start_date: date = Query(..., description="Start date of range"),
    end_date: date = Query(..., description="End date of range"),
    user_id: UUID = Depends(get_current_user_id),
    service: DailySummaryService = Depends(get_daily_summary_service)
):
    """
    Get weekly nutrition trends for a date range.

    Returns:
    - Daily averages (calories, macros, meal count)
    - Daily data for each day in range
    - Trend analysis (increasing, decreasing, stable)
    - Variance and consistency score

    **Example Response:**
    ```json
    {
      "date_range": ["2024-10-08", "2024-10-14"],
      "days_with_data": 7,
      "daily_averages": {
        "calories": 2150.0,
        "protein": 158.5,
        "consistency_score": 0.92
      },
      "daily_data": [
        {
          "date": "2024-10-08",
          "calories": 2300,
          "protein": 165.0,
          ...
        }
      ],
      "trend": "stable",
      "variance": 8.5
    }
    ```

    **Use Cases:**
    - Dashboard weekly chart
    - Progress tracking
    - Consistency analysis
    """
    # Validate date range
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be >= start_date"
        )

    # Limit to 30 days
    if (end_date - start_date).days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 30 days"
        )

    try:
        trends = await service.get_weekly_trends(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return trends
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating weekly trends: {str(e)}"
        )


@router.get("/weekly-trends/last-7-days", response_model=WeeklyTrends)
async def get_last_7_days_trends(
    user_id: UUID = Depends(get_current_user_id),
    service: DailySummaryService = Depends(get_daily_summary_service)
):
    """
    Get weekly trends for the last 7 days.

    Convenience endpoint that automatically calculates the date range.

    **Example Response:**
    Same as `/weekly-trends/range` but for last 7 days.

    **Use Cases:**
    - Quick dashboard widget
    - "This week" summary
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=6)  # Last 7 days including today

    try:
        trends = await service.get_weekly_trends(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return trends
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating weekly trends: {str(e)}"
        )


@router.get("/compare", response_model=ComparisonResult)
async def compare_days(
    dates: List[date] = Query(..., description="List of dates to compare (comma-separated)"),
    user_id: UUID = Depends(get_current_user_id),
    service: DailySummaryService = Depends(get_daily_summary_service)
):
    """
    Compare nutrition across multiple days.

    Returns:
    - Nutrition data for each day
    - Difference calculation (for 2 days)
    - Text analysis of comparison

    **Example Request:**
    ```
    GET /daily-summary/compare?dates=2024-10-13&dates=2024-10-14
    ```

    **Example Response (2 days):**
    ```json
    {
      "days": [
        {
          "date": "2024-10-13",
          "calories": 2300,
          "protein": 165.0,
          ...
        },
        {
          "date": "2024-10-14",
          "calories": 1850,
          "protein": 145.0,
          ...
        }
      ],
      "difference": {
        "calories": -450,
        "protein": -20.0,
        "calories_percent": -19.6
      },
      "analysis": "You consumed 450 fewer calories on 2024-10-14 (-19.6%)."
    }
    ```

    **Use Cases:**
    - Yesterday vs today comparison
    - Before/after analysis
    - Multi-day comparison
    """
    if not dates or len(dates) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide at least 2 dates to compare"
        )

    if len(dates) > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare more than 7 days at once"
        )

    try:
        comparison = await service.compare_days(
            user_id=user_id,
            dates=dates
        )
        return comparison
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing days: {str(e)}"
        )


@router.get("/projection/today", response_model=DailySummaryResponse)
async def get_today_with_projection(
    user_id: UUID = Depends(get_current_user_id),
    service: DailySummaryService = Depends(get_daily_summary_service)
):
    """
    Get today's summary with end-of-day projection.

    Convenience endpoint for getting current progress with projection.

    **Example Response:**
    Same as `/daily-summary/{date}` but always for today with projection enabled.

    **Use Cases:**
    - Real-time dashboard
    - "How am I doing today?" widget
    - Meal planning recommendations
    """
    today = date.today()

    try:
        summary = await service.get_daily_summary(
            user_id=user_id,
            target_date=today,
            include_projection=True
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating today's summary: {str(e)}"
        )


@router.get("/stats/current-week", response_model=dict)
async def get_current_week_stats(
    user_id: UUID = Depends(get_current_user_id),
    service: DailySummaryService = Depends(get_daily_summary_service)
):
    """
    Get quick stats for the current week (Monday-Sunday).

    Returns:
    - Days logged this week
    - Average calories
    - Total deficit/surplus
    - Consistency score

    **Example Response:**
    ```json
    {
      "week_start": "2024-10-07",
      "week_end": "2024-10-13",
      "days_logged": 6,
      "average_calories": 2150,
      "total_deficit": 350,
      "consistency_score": 0.88,
      "trend": "stable"
    }
    ```

    **Use Cases:**
    - Quick dashboard widget
    - Weekly progress card
    """
    # Calculate current week (Monday to Sunday)
    today = date.today()
    days_since_monday = today.weekday()  # Monday = 0, Sunday = 6
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)

    try:
        trends = await service.get_weekly_trends(
            user_id=user_id,
            start_date=week_start,
            end_date=week_end
        )

        # Get today's summary for deficit calculation
        today_summary = await service.get_daily_summary(
            user_id=user_id,
            target_date=today,
            include_projection=False
        )

        total_deficit = 0
        if today_summary.calorie_balance:
            total_deficit = today_summary.calorie_balance.deficit * trends.days_with_data

        return {
            "week_start": str(week_start),
            "week_end": str(week_end),
            "days_logged": trends.days_with_data,
            "average_calories": round(trends.daily_averages.calories, 0),
            "total_deficit": total_deficit,
            "consistency_score": trends.consistency_score,
            "trend": trends.trend
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating week stats: {str(e)}"
        )
