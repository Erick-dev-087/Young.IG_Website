from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from src.enums import ImageCategory


class InspectionImageCreate(BaseModel):
    image_url: str = Field(..., min_length=5)
    image_category: Optional[ImageCategory] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_url": "https://res.cloudinary.com/youngig/image/upload/v123/engine_front.jpg",
                "image_category": "ENGINE"
            }
        }
    }


class InspectionImageUpdate(BaseModel):
    image_url: Optional[str] = Field(None, min_length=5)
    image_category: Optional[ImageCategory] = None


from uuid import UUID

class InspectionImageResponse(BaseModel):
    id: UUID
    image_url: str
    image_category: Optional[ImageCategory] = None
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
