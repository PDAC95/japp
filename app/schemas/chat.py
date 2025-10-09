"""
Chat API Schemas

Pydantic models for chat and food extraction endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict


class FoodItem(BaseModel):
    """Individual food item with nutrition data"""
    name: str = Field(..., description="Food name", min_length=1)
    quantity: float = Field(..., description="Quantity amount", gt=0)
    unit: str = Field(..., description="Unit of measurement (g, ml, piece, serving)")
    calories: float = Field(..., description="Total calories", ge=0)
    protein_g: float = Field(..., description="Protein in grams", ge=0)
    carbs_g: float = Field(..., description="Carbohydrates in grams", ge=0)
    fat_g: float = Field(..., description="Fat in grams", ge=0)

    @validator('calories', 'protein_g', 'carbs_g', 'fat_g')
    def no_negative_nutrition(cls, v):
        """Ensure no negative nutrition values"""
        if v < 0:
            raise ValueError('Nutrition values cannot be negative')
        return round(v, 2)

    @validator('quantity')
    def positive_quantity(cls, v):
        """Ensure quantity is positive"""
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return round(v, 2)


class MacroSummary(BaseModel):
    """Summary of macronutrients"""
    protein: float = Field(..., description="Total protein in grams", ge=0)
    carbs: float = Field(..., description="Total carbs in grams", ge=0)
    fat: float = Field(..., description="Total fat in grams", ge=0)


class FoodExtractionRequest(BaseModel):
    """Request to extract food from natural language text"""
    text: str = Field(
        ...,
        description="Natural language food description",
        min_length=1,
        max_length=1000,
        example="Comí 2 tacos de carnitas con salsa verde"
    )

    @validator('text')
    def text_not_empty(cls, v):
        """Ensure text is not just whitespace"""
        if not v.strip():
            raise ValueError('Food description cannot be empty')
        return v.strip()


class FoodExtractionResponse(BaseModel):
    """Response containing extracted food data"""
    foods: List[FoodItem] = Field(..., description="List of extracted food items")
    total_calories: float = Field(..., description="Total calories for all foods", ge=0)
    total_macros: MacroSummary = Field(..., description="Total macros for all foods")
    message: Optional[str] = Field(None, description="Optional coaching message")
    error: Optional[str] = Field(None, description="Error message if extraction failed")


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    content: str = Field(
        ...,
        description="Message content",
        min_length=1,
        max_length=2000
    )
    extract_food: bool = Field(
        True,
        description="Whether to extract food data from message"
    )


class ChatMessageResponse(BaseModel):
    """Response from chat endpoint"""
    response: str = Field(..., description="AI coach response")
    extracted_data: Optional[FoodExtractionResponse] = Field(
        None,
        description="Extracted food data if extract_food was True"
    )
