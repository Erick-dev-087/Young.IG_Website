from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

from src.enums import OdoMeasure, InspectionStatus, OverallCondition
from src.schemas.inspection_result import InspectionResultResponse
from src.schemas.inspection_image import InspectionImageResponse


class InspectionCreate(BaseModel):
    inspection_number: str = Field(..., min_length=3, max_length=50)
    inspection_date: date
    inspector_id: UUID
    customer_id: Optional[UUID] = None
    vehicle_id: UUID
    mileage: Optional[int] = Field(None, ge=0)
    odo_measure: Optional[OdoMeasure] = OdoMeasure.KMS
    mileage_authentic: Optional[bool] = None
    seller_name: Optional[str] = Field(None, max_length=255)

    model_config = {
        "json_schema_extra": {
            "example": {
                "inspection_number": "YIG-2026-001",
                "inspection_date": "2026-07-17",
                "inspector_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "customer_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "vehicle_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "mileage": 85000,
                "odo_measure": "KMS",
                "mileage_authentic": True,
                "seller_name": "Kamau Motors"
            }
        }
    }


class InspectionUpdate(BaseModel):
    inspection_date: Optional[date] = None
    mileage: Optional[int] = Field(None, ge=0)
    odo_measure: Optional[OdoMeasure] = None
    mileage_authentic: Optional[bool] = None
    seller_name: Optional[str] = Field(None, max_length=255)
    status: Optional[InspectionStatus] = None
    final_notes: Optional[str] = None
    overall_condition: Optional[OverallCondition] = None
    pdf_url: Optional[str] = None


class InspectionResponse(BaseModel):
    id: UUID
    inspection_number: str
    inspection_date: date
    inspector_id: UUID
    customer_id: Optional[UUID] = None
    vehicle_id: UUID
    mileage: Optional[int] = None
    odo_measure: Optional[OdoMeasure] = None
    mileage_authentic: Optional[bool] = None
    seller_name: Optional[str] = None
    status: Optional[InspectionStatus] = None
    final_notes: Optional[str] = None
    overall_condition: Optional[OverallCondition] = None
    pdf_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InspectionFullResponse(InspectionResponse):
    """
    Extended response that includes all nested results and images.
    Used when fetching a single inspection in detail.
    """
    results: List[InspectionResultResponse] = []
    images: List[InspectionImageResponse] = []
