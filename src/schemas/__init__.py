"""
Pydantic schemas for the Young IG Auto Inspection System.
"""

from src.schemas.user import UserCreate, UserUpdate, UserAdminUpdate, UserResponse
from src.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from src.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from src.schemas.inspection_category import (
    InspectionCategoryCreate,
    InspectionCategoryUpdate,
    InspectionCategoryResponse,
    InspectionCategoryFullResponse,
)
from src.schemas.inspection_field import (
    InspectionFieldCreate,
    InspectionFieldUpdate,
    InspectionFieldResponse,
)
from src.schemas.inspection_result import (
    InspectionResultCreate,
    InspectionResultUpdate,
    InspectionResultResponse,
)
from src.schemas.inspection_image import (
    InspectionImageCreate,
    InspectionImageUpdate,
    InspectionImageResponse,
)
from src.schemas.inspection import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    InspectionFullResponse,
)

__all__ = [
    # User
    "UserCreate", "UserUpdate", "UserAdminUpdate", "UserResponse",
    # Customer
    "CustomerCreate", "CustomerUpdate", "CustomerResponse",
    # Vehicle
    "VehicleCreate", "VehicleUpdate", "VehicleResponse",
    # Inspection Category
    "InspectionCategoryCreate", "InspectionCategoryUpdate",
    "InspectionCategoryResponse", "InspectionCategoryFullResponse",
    # Inspection Field
    "InspectionFieldCreate", "InspectionFieldUpdate", "InspectionFieldResponse",
    # Inspection Result
    "InspectionResultCreate", "InspectionResultUpdate", "InspectionResultResponse",
    # Inspection Image
    "InspectionImageCreate", "InspectionImageUpdate", "InspectionImageResponse",
    # Inspection
    "InspectionCreate", "InspectionUpdate", "InspectionResponse", "InspectionFullResponse",
]
