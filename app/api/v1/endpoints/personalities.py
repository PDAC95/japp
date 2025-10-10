"""
Personalities Endpoint

Handles CRUD operations for coach personality types.
Personalities are loaded dynamically from the database.
"""

from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
import logging

from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class PersonalityType(BaseModel):
    """Personality type response model"""
    id: str
    code: str
    name: str
    description: str
    example_response: str | None = None
    display_order: int

    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[PersonalityType])
async def list_personalities():
    """
    Get all active personality types.

    Returns personalities ordered by display_order.
    These are used in the personality selector UI.

    **Returns:**
    - List of active personality types

    **Raises:**
    - 500: Database error
    """
    try:
        supabase = get_supabase_client()

        # Query active personalities ordered by display_order
        response = supabase.table('personality_types') \
            .select('id, code, name, description, example_response, display_order') \
            .eq('is_active', True) \
            .order('display_order') \
            .execute()

        if not response.data:
            logger.warning("No active personalities found in database")
            return []

        logger.info(f"Retrieved {len(response.data)} active personalities")
        return response.data

    except Exception as e:
        logger.error(f"Error fetching personalities: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch personality types"
        )


@router.get("/{code}", response_model=PersonalityType)
async def get_personality(code: str):
    """
    Get a specific personality type by code.

    **Parameters:**
    - code: Personality code (e.g., 'friendly', 'strict', 'motivational')

    **Returns:**
    - Personality type details

    **Raises:**
    - 404: Personality not found
    - 500: Database error
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table('personality_types') \
            .select('id, code, name, description, example_response, display_order') \
            .eq('code', code) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Personality '{code}' not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching personality '{code}': {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch personality type"
        )


@router.get("/{code}/instructions")
async def get_personality_instructions(code: str):
    """
    Get prompt instructions for a specific personality.

    Internal endpoint used by chat service to build Claude prompts.

    **Parameters:**
    - code: Personality code

    **Returns:**
    - Prompt instructions for Claude

    **Raises:**
    - 404: Personality not found
    - 500: Database error
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table('personality_types') \
            .select('prompt_instructions') \
            .eq('code', code) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if not response.data:
            # Fallback to friendly if personality not found
            logger.warning(f"Personality '{code}' not found, using 'friendly' as fallback")
            response = supabase.table('personality_types') \
                .select('prompt_instructions') \
                .eq('code', 'friendly') \
                .single() \
                .execute()

        return {
            "code": code,
            "instructions": response.data['prompt_instructions']
        }

    except Exception as e:
        logger.error(f"Error fetching instructions for '{code}': {e}")
        # Return fallback instructions
        return {
            "code": "friendly",
            "instructions": "You are a warm, supportive nutrition coach. Be encouraging and understanding."
        }
