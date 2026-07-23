from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

from src.enums import FieldInputType


class InspectionFieldCreate(BaseModel):
    category_id: int = Field(..., ge=1)
    field_name: str = Field(..., min_length=2, max_length=255)
    field_key: str = Field(..., min_length=2, max_length=100)
    input_type: FieldInputType
    options: Optional[Dict[str, Any]] = None
    is_required: bool = True
    display_order: Optional[int] = Field(None, ge=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "category_id": 1,
                "field_name": "Engine Oil Condition",
                "field_key": "engine_oil_condition",
                "input_type": "SELECT",
                "options": {"choices": ["Good", "Fair", "Poor"]},
                "is_required": True,
                "display_order": 1
            }
        }
    }


class InspectionFieldUpdate(BaseModel):
    field_name: Optional[str] = Field(None, min_length=2, max_length=255)
    input_type: Optional[FieldInputType] = None
    options: Optional[Dict[str, Any]] = None
    is_required: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=1)


class InspectionFieldResponse(BaseModel):
    id: int
    field_name: str
    field_key: str
    input_type: FieldInputType
    options: Optional[Dict[str, Any]] = None
    is_required: bool
    display_order: Optional[int] = None

    model_config = {"from_attributes": True}
