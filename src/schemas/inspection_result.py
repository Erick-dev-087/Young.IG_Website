from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from src.schemas.inspection_field import InspectionFieldResponse


class InspectionResultCreate(BaseModel):
    inspection_field_id: int = Field(..., ge=1)
    filed_value: Optional[str] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "inspection_field_id": 5,
                "filed_value": "Good",
                "notes": "No visible leaks or discoloration."
            }
        }
    }


class InspectionResultUpdate(BaseModel):
    filed_value: Optional[str] = None
    notes: Optional[str] = None


from uuid import UUID

class InspectionResultResponse(BaseModel):
    id: UUID
    inspection_field_id: int
    filed_value: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    # Nested field info so the consumer knows what field this result belongs to
    field: Optional[InspectionFieldResponse] = None

    model_config = {"from_attributes": True}
