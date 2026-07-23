"""
Upload Service — Young IG Auto Inspection System

Handles uploading inspection images to Cloudinary and storing the
returned URLs in the database as InspectionImage records.

Each uploaded image is:
  1. Tagged with an ImageCategory (EXTERIOR, ENGINE, INTERIOR, etc.)
  2. Stored in a Cloudinary folder organized by inspection number
  3. Saved to the inspection_images table with its URL
"""

import uuid
from typing import List, Dict, Any, Optional
from uuid import UUID

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..config import settings
from ..model import InspectionImage, Inspection
from ..enums import ImageCategory, InspectionStatus


def _configure_cloudinary():
    """Ensures Cloudinary SDK is configured. Safe to call multiple times."""
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


class UploadService:
    """
    Manages image uploads to Cloudinary and links them to inspections.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        _configure_cloudinary()

    async def upload_inspection_image(
        self,
        inspection_id: UUID,
        file: UploadFile,
        image_category: ImageCategory,
    ) -> InspectionImage:
        """
        Upload a single image to Cloudinary and create an InspectionImage record.

        The image is stored in a folder structure:
          young_ig_inspections/{inspection_number}/{category}_{uuid}

        Returns the created InspectionImage ORM object with the Cloudinary URL.
        """
        # 1. Validate the inspection exists and is editable
        from sqlalchemy import select
        result = await self.db.execute(
            select(Inspection).where(Inspection.id == inspection_id)
        )
        inspection = result.scalar_one_or_none()

        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found.",
            )

        if inspection.status not in (InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot upload images to a '{inspection.status.value}' inspection.",
            )

        # 2. Validate the file is an image
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File must be an image. Got: {file.content_type}",
            )

        # 3. Upload to Cloudinary
        folder = f"{settings.cloudinary_folder}/{inspection.inspection_number}"
        public_id = f"{image_category.value.lower()}_{uuid.uuid4().hex[:8]}"

        try:
            file_content = await file.read()
            upload_result = cloudinary.uploader.upload(
                file_content,
                folder=folder,
                public_id=public_id,
                resource_type="image",
                overwrite=False,
                transformation=[
                    {"quality": "auto:good", "fetch_format": "auto"}
                ],
            )
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Image upload to storage failed. Please try again.",
            )
        finally:
            await file.seek(0)  # reset file pointer in case caller needs it

        image_url = upload_result.get("secure_url", upload_result.get("url"))

        # 4. Create the database record
        image_record = InspectionImage(
            inspection_id=inspection_id,
            image_url=image_url,
            image_category=image_category,
        )
        self.db.add(image_record)
        await self.db.flush()
        await self.db.refresh(image_record)

        logger.info(
            f"Image uploaded: {image_category.value} for inspection "
            f"{inspection.inspection_number} -> {image_url}"
        )
        return image_record

    async def upload_batch(
        self,
        inspection_id: UUID,
        files: List[UploadFile],
        categories: List[ImageCategory],
    ) -> Dict[str, Any]:
        """
        Upload multiple images at once, each with its own category.
        The lists must be the same length (1-to-1 mapping).
        """
        if len(files) != len(categories):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mismatch: {len(files)} files but {len(categories)} categories.",
            )

        uploaded = []
        for file, category in zip(files, categories):
            record = await self.upload_inspection_image(inspection_id, file, category)
            uploaded.append({
                "image_id": str(record.id),
                "image_url": record.image_url,
                "category": category.value,
            })

        logger.info(f"Batch upload complete: {len(uploaded)} images for inspection {inspection_id}")
        return {
            "inspection_id": str(inspection_id),
            "images_uploaded": len(uploaded),
            "images": uploaded,
        }

    async def delete_image(self, image_id: UUID) -> Dict[str, str]:
        """
        Delete an inspection image from both Cloudinary and the database.
        """
        from sqlalchemy import select, delete

        result = await self.db.execute(
            select(InspectionImage).where(InspectionImage.id == image_id)
        )
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found.",
            )

        # Attempt to delete from Cloudinary (extract public_id from URL)
        try:
            # Cloudinary URLs look like: .../v1234567/folder/subfolder/public_id.ext
            url_parts = image.image_url.split("/")
            # Get everything after "upload/" and remove the extension
            upload_idx = url_parts.index("upload")
            public_id_parts = url_parts[upload_idx + 2:]  # skip version number
            public_id = "/".join(public_id_parts).rsplit(".", 1)[0]
            cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception as e:
            logger.warning(f"Could not delete from Cloudinary (non-blocking): {e}")

        # Delete from database
        await self.db.execute(
            delete(InspectionImage).where(InspectionImage.id == image_id)
        )
        await self.db.flush()

        logger.info(f"Image deleted: {image_id}")
        return {"message": "Image deleted successfully."}
