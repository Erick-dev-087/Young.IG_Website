from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from src.enums import FuelType, Transmission, VehicleType


class VehicleCreate(BaseModel):
    registration_number: str = Field(..., min_length=4, max_length=30)
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    engine_number: Optional[str] = Field(None, max_length=100)
    chassis_number: Optional[str] = Field(None, max_length=100)
    manufacture_year: Optional[int] = Field(None, ge=1900, le=2100)
    fuel_type: Optional[FuelType] = None
    transmission: Optional[Transmission] = None
    vehicle_type: Optional[VehicleType] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "registration_number": "KAA 123A",
                "make": "Toyota",
                "model": "Fielder",
                "engine_number": "1NZ-1234567",
                "chassis_number": "NZE1410012345",
                "manufacture_year": 2015,
                "fuel_type": "PETROL",
                "transmission": "AUTOMATIC",
                "vehicle_type": "INTERNAL_COMBUSTION"
            }
        }
    }


class VehicleUpdate(BaseModel):
    registration_number: Optional[str] = Field(None, min_length=4, max_length=30)
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    engine_number: Optional[str] = Field(None, max_length=100)
    chassis_number: Optional[str] = Field(None, max_length=100)
    manufacture_year: Optional[int] = Field(None, ge=1900, le=2100)
    fuel_type: Optional[FuelType] = None
    transmission: Optional[Transmission] = None
    vehicle_type: Optional[VehicleType] = None


class VehicleResponse(BaseModel):
    id: UUID
    registration_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    manufacture_year: Optional[int] = None
    fuel_type: Optional[FuelType] = None
    transmission: Optional[Transmission] = None
    vehicle_type: Optional[VehicleType] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
