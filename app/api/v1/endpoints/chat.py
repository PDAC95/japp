"""
Chat API Endpoints

Handles AI-powered chat and food extraction functionality.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from app.schemas.chat import (
    FoodExtractionRequest,
    FoodExtractionResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    FoodItem,
    MacroSummary
)
from app.services.claude_service import get_claude_service, ClaudeService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract", response_model=Dict[str, Any])
async def extract_food_from_text(
    request: FoodExtractionRequest,
    claude_service: ClaudeService = Depends(get_claude_service)
) -> Dict[str, Any]:
    """
    Extract food items and nutrition data from natural language text.

    This endpoint accepts casual food descriptions in English or Spanish
    and returns structured nutrition data using Claude AI.

    **Examples:**
    - "Comí 2 tacos de carnitas" → extracts tacos with nutrition
    - "3 eggs and toast" → extracts eggs and toast separately
    - "un plato de feijoada" → understands Brazilian portions

    **Returns:**
    - success: bool
    - data: FoodExtractionResponse with foods array and totals
    - message: Success message
    - error: Error details if failed
    """
    try:
        logger.info(f"Extracting food from text: '{request.text[:50]}...'")

        # Call Claude service
        extraction_result = await claude_service.extract_food_from_text(request.text)

        # Check if extraction failed
        if "error" in extraction_result and extraction_result["error"]:
            return {
                "success": False,
                "data": None,
                "message": None,
                "error": {
                    "message": extraction_result["error"],
                    "code": "EXTRACTION_FAILED",
                    "statusCode": 422
                }
            }

        # Build response
        foods = [FoodItem(**food) for food in extraction_result["foods"]]

        response_data = FoodExtractionResponse(
            foods=foods,
            total_calories=extraction_result["total_calories"],
            total_macros=MacroSummary(**extraction_result["total_macros"]),
            message=extraction_result.get("message"),
            error=None
        )

        return {
            "success": True,
            "data": response_data.model_dump(),
            "message": f"Extracted {len(foods)} food item(s)",
            "error": None
        }

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "data": None,
                "message": None,
                "error": {
                    "message": str(e),
                    "code": "VALIDATION_ERROR",
                    "statusCode": 422
                }
            }
        )

    except TimeoutError as e:
        logger.error(f"Claude API timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail={
                "success": False,
                "data": None,
                "message": None,
                "error": {
                    "message": "AI service timeout - please try again",
                    "code": "CLAUDE_TIMEOUT",
                    "statusCode": 504
                }
            }
        )

    except Exception as e:
        logger.error(f"Unexpected error in food extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "message": None,
                "error": {
                    "message": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "statusCode": 500
                }
            }
        )


@router.post("/message", response_model=Dict[str, Any])
async def send_chat_message(
    request: ChatMessageRequest,
    claude_service: ClaudeService = Depends(get_claude_service)
) -> Dict[str, Any]:
    """
    Send a message to the AI health coach.

    Optionally extracts food data if the message contains food descriptions.

    **Returns:**
    - success: bool
    - data: ChatMessageResponse with AI response and optional extracted food data
    - message: Success message
    """
    try:
        logger.info(f"Processing chat message: '{request.content[:50]}...'")

        # For now, we'll just extract food if requested
        # Full conversational chat will be implemented in US-034
        extracted_data = None

        if request.extract_food:
            extraction_result = await claude_service.extract_food_from_text(request.content)

            if "error" not in extraction_result or not extraction_result["error"]:
                foods = [FoodItem(**food) for food in extraction_result["foods"]]

                extracted_data = FoodExtractionResponse(
                    foods=foods,
                    total_calories=extraction_result["total_calories"],
                    total_macros=MacroSummary(**extraction_result["total_macros"]),
                    message=extraction_result.get("message"),
                    error=None
                )

        # Build chat response
        response_data = ChatMessageResponse(
            response=extracted_data.message if extracted_data else "Message received",
            extracted_data=extracted_data
        )

        return {
            "success": True,
            "data": response_data.model_dump(),
            "message": "Message processed successfully",
            "error": None
        }

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "message": None,
                "error": {
                    "message": "Failed to process message",
                    "code": "CHAT_ERROR",
                    "statusCode": 500
                }
            }
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for chat service.

    Verifies that Claude service is properly initialized.
    """
    try:
        claude_service = get_claude_service()
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "model": claude_service.model,
                "max_tokens": claude_service.max_tokens,
                "temperature": claude_service.temperature
            },
            "message": "Chat service is healthy",
            "error": None
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "data": None,
            "message": None,
            "error": {
                "message": str(e),
                "code": "SERVICE_UNHEALTHY",
                "statusCode": 503
            }
        }
