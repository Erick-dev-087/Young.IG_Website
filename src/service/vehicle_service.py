"""
Vehicle Service — Young IG Auto Inspection System

Handles vehicle registration, lookups (by reg, chassis, engine, make, model,
fuel type, transmission, vehicle type), problem search, and full vehicle history.
"""

from uuid import UUID
from datetime import date
from typing import List, Optional, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..model import Vehicle, Inspection
from ..repositories.vehicle_repository import VehicleRepository
from ..Schemas.vehicle import VehicleCreate, VehicleUpdate
from ..enums import FuelType, Transmission, VehicleType


class VehicleService:
    """
    Business logic for vehicle management, search, and history.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vehicle_repo = VehicleRepository(db)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def register(self, data: VehicleCreate) -> Vehicle:
        """
        Register a new vehicle. Prevents duplicate registration numbers.
        If a vehicle with the same reg number already exists, returns it
        instead of creating a duplicate (idempotent for inspections workflow).
        """
        existing = await self.vehicle_repo.get_by_registration_number(
            data.registration_number
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle with registration '{data.registration_number}' already exists.",
            )

        vehicle = await self.vehicle_repo.create(**data.model_dump())
        logger.info(f"Vehicle registered: {vehicle.registration_number}")
        return vehicle

    async def get_or_create(self, data: VehicleCreate) -> Vehicle:
        """
        Returns the existing vehicle if the registration number matches,
        otherwise creates a new one. This is the method the inspection
        workflow should use — it avoids duplicates without raising errors.
        """
        existing = await self.vehicle_repo.get_by_registration_number(
            data.registration_number
        )
        if existing:
            return existing

        vehicle = await self.vehicle_repo.create(**data.model_dump())
        logger.info(f"Vehicle registered: {vehicle.registration_number}")
        return vehicle

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehicle], int]:
        return await self.vehicle_repo.get_all(skip=skip, limit=limit)

    async def get_by_id(self, vehicle_id: UUID) -> Vehicle:
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found.",
            )
        return vehicle

    async def update(self, vehicle_id: UUID, data: VehicleUpdate) -> Vehicle:
        """
        Update vehicle details. Validates reg number uniqueness if it's being changed.
        """
        vehicle = await self.get_by_id(vehicle_id)
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        # If reg number is changing, check for duplicates
        if "registration_number" in update_data:
            new_reg = update_data["registration_number"]
            if new_reg != vehicle.registration_number:
                existing = await self.vehicle_repo.get_by_registration_number(new_reg)
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Vehicle with registration '{new_reg}' already exists.",
                    )

        updated = await self.vehicle_repo.update(vehicle_id, **update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update vehicle.",
            )
        logger.info(f"Vehicle updated: {updated.registration_number}")
        return updated

    async def delete(self, vehicle_id: UUID) -> Dict[str, str]:
        vehicle = await self.get_by_id(vehicle_id)
        await self.vehicle_repo.hard_delete(vehicle_id)
        logger.info(f"Vehicle deleted: {vehicle.registration_number}")
        return {"message": f"Vehicle '{vehicle.registration_number}' has been removed."}

    # ------------------------------------------------------------------
    # LOOKUPS — All the search methods from the repository
    # ------------------------------------------------------------------

    async def get_by_registration_number(self, reg_no: str) -> Vehicle:
        vehicle = await self.vehicle_repo.get_by_registration_number(reg_no)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No vehicle found with registration '{reg_no}'.",
            )
        return vehicle

    async def get_by_engine_number(self, engine_no: str) -> Vehicle:
        vehicle = await self.vehicle_repo.get_by_engine_number(engine_no)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No vehicle found with engine number '{engine_no}'.",
            )
        return vehicle

    async def get_by_chassis_number(self, chassis_no: str) -> Vehicle:
        vehicle = await self.vehicle_repo.get_by_chassis_number(chassis_no)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No vehicle found with chassis number '{chassis_no}'.",
            )
        return vehicle

    async def get_by_make(
        self, make: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehicle], int]:
        return await self.vehicle_repo.get_by_make(make, skip=skip, limit=limit)

    async def get_by_model(
        self, model_name: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehicle], int]:
        return await self.vehicle_repo.get_by_model(model_name, skip=skip, limit=limit)

    async def get_by_fuel_type(
        self, fuel_type: FuelType, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehicle], int]:
        return await self.vehicle_repo.get_by_fuel_type(fuel_type, skip=skip, limit=limit)

    async def get_by_transmission(
        self, transmission: Transmission, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehicle], int]:
        return await self.vehicle_repo.get_by_transmission(transmission, skip=skip, limit=limit)

    async def get_by_vehicle_type(
        self, vehicle_type: VehicleType, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Vehicle], int]:
        return await self.vehicle_repo.get_by_vehicle_type(vehicle_type, skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # PROBLEM SEARCH & HISTORY
    # ------------------------------------------------------------------

    async def find_vehicles_with_problem(
        self,
        field_name: str,
        problem_value: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Vehicle], int]:
        """
        Find all vehicles that had a specific problem recorded during inspection.
        E.g. field_name="Engine Health", problem_value="Poor"
        """
        return await self.vehicle_repo.get_vehicles_with_problem(
            field_name, problem_value, skip=skip, limit=limit
        )

    async def get_vehicle_history(self, vehicle_id: UUID) -> Dict[str, Any]:
        """
        Get the full inspection history of a vehicle.
        Returns the vehicle details along with all past inspections
        (including results, images, inspector, and customer info).
        """
        vehicle = await self.get_by_id(vehicle_id)
        inspections = await self.vehicle_repo.get_vehicle_history(vehicle_id)

        return {
            "vehicle": vehicle,
            "total_inspections": len(inspections),
            "inspections": inspections,
        }

    async def get_vehicle_history_by_reg(self, registration_number: str) -> Dict[str, Any]:
        """
        Convenience method: look up history by registration number instead of UUID.
        This is what the frontend will typically call since users know reg numbers, not UUIDs.
        """
        vehicle = await self.get_by_registration_number(registration_number)
        inspections = await self.vehicle_repo.get_vehicle_history(vehicle.id)

        return {
            "vehicle": vehicle,
            "total_inspections": len(inspections),
            "inspections": inspections,
        }
