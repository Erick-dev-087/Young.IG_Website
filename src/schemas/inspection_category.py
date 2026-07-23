from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING


if TYPE_CHECKING:
    from src.schemas.inspection_field import InspectionFieldResponse


class InspectionCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    display_order: Optional[int] = Field(None, ge=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Engine & Powertrain",
                "display_order": 1
            }
        }
    }


class InspectionCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    display_order: Optional[int] = Field(None, ge=1)


class InspectionCategoryResponse(BaseModel):
    id: int
    name: str
    display_order: Optional[int] = None

    model_config = {"from_attributes": True}


class InspectionCategoryFullResponse(InspectionCategoryResponse):
    """Response that also embeds all fields belonging to this category."""
    fields: List["InspectionFieldResponse"] = []


# Resolve forward reference after the field schema is importable at runtime
from src.schemas.inspection_field import InspectionFieldResponse    # noqa: E402
InspectionCategoryFullResponse.model_rebuild()
