from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


from src.enums import CustomerType


class CustomerCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    kra_pin: Optional[str] = Field(None, max_length=50)
    customer_type: CustomerType = CustomerType.INDIVIDUAL

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Jane Wanjiku",
                "email": "jane@example.com",
                "phone": "0712345678",
                "kra_pin": "A123456789B",
                "customer_type": "INDIVIDUAL"
            }
        }
    }


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    kra_pin: Optional[str] = Field(None, max_length=50)
    customer_type: Optional[CustomerType] = None



class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    kra_pin: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CustomerHistoryResponse(BaseModel):
    """Used for returning a customer along with all their past inspections."""
    customer: CustomerResponse
    # We will use Any or a generic dict here to avoid circular imports with inspection.py, 
    # but in the actual route we can return the InspectionResponse
    total_inspections: int
    inspections: list = []

class CustomerServedMetricsResponse(BaseModel):
    """Metrics for customers served in a specific timeframe."""
    timeframe_start: str
    timeframe_end: str
    total_customers_served: int
    new_customers: int
    returning_customers: int

class CustomerPerformanceDashboardResponse(BaseModel):
    """High-level dashboard metrics for the business."""
    total_customers_in_system: int
    customers_served_today: int
    customers_served_this_week: int
    customers_served_this_month: int

class TopCustomerResponse(BaseModel):
    """Used for ranking top customers."""
    customer_id: UUID
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    total_inspections: int
