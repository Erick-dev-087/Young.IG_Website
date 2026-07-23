from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Tuple, Optional
from uuid import UUID

from .base import BaseRepository
from src.model import Vehicle, Inspection, InspectionResult, InspectionField
from src.enums import FuelType, Transmission, VehicleType

class VehicleRepository(BaseRepository[Vehicle]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(Vehicle, db_session)

    async def get_by_registration_number(self, registration_number: str) -> Optional[Vehicle]:
        """Get a vehicle by its registration number"""
        query = select(Vehicle).where(Vehicle.registration_number == registration_number)
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_by_make(self, make: str, skip: int = 0, limit: int = 100) -> Tuple[List[Vehicle], int]:
        """Get vehicles by make with pagination"""
        query = select(Vehicle).where(Vehicle.make.ilike(f"%{make}%"))
        count_query = select(func.count(Vehicle.id)).where(Vehicle.make.ilike(f"%{make}%"))
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_by_model(self, model_name: str, skip: int = 0, limit: int = 100) -> Tuple[List[Vehicle], int]:
        """Get vehicles by model with pagination"""
        query = select(Vehicle).where(Vehicle.model.ilike(f"%{model_name}%"))
        count_query = select(func.count(Vehicle.id)).where(Vehicle.model.ilike(f"%{model_name}%"))
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0


    async def get_by_fuel_type(self, fuel_type: FuelType, skip: int = 0, limit: int = 100) -> Tuple[List[Vehicle], int]:
        """Get vehicles by fuel type with pagination"""
        query = select(Vehicle).where(Vehicle.fuel_type == fuel_type)
        count_query = select(func.count(Vehicle.id)).where(Vehicle.fuel_type == fuel_type)
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_by_transmission(self, transmission: Transmission, skip: int = 0, limit: int = 100) -> Tuple[List[Vehicle], int]:
        """Get vehicles by transmission with pagination"""
        query = select(Vehicle).where(Vehicle.transmission == transmission)
        count_query = select(func.count(Vehicle.id)).where(Vehicle.transmission == transmission)
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_by_vehicle_type(self, vehicle_type: VehicleType, skip: int = 0, limit: int = 100) -> Tuple[List[Vehicle], int]:
        """Get vehicles by vehicle type with pagination"""
        query = select(Vehicle).where(Vehicle.vehicle_type == vehicle_type)
        count_query = select(func.count(Vehicle.id)).where(Vehicle.vehicle_type == vehicle_type)
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_by_engine_number(self, engine_number: str) -> Optional[Vehicle]:
        """Get a vehicle by its engine number"""
        query = select(Vehicle).where(Vehicle.engine_number == engine_number)
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_by_chassis_number(self, chassis_number: str) -> Optional[Vehicle]:
        """Get a vehicle by its chassis number"""
        query = select(Vehicle).where(Vehicle.chassis_number == chassis_number)
        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def get_vehicles_with_problem(self, field_name: str, problem_value: str, skip: int = 0, limit: int = 100) -> Tuple[List[Vehicle], int]:
        """
        Get all vehicles that have a specific problem recorded in an inspection.
        E.g. field_name="Engine Health", problem_value="Poor"
        """
        # Join Vehicle -> Inspection -> InspectionResult -> InspectionField
        query = (
            select(Vehicle)
            .join(Inspection, Inspection.vehicle_id == Vehicle.id)
            .join(InspectionResult, InspectionResult.inspection_id == Inspection.id)
            .join(InspectionField, InspectionField.id == InspectionResult.inspection_field_id)
            .where(
                and_(
                    InspectionField.field_name.ilike(f"%{field_name}%"),
                    InspectionResult.filed_value.ilike(f"%{problem_value}%")
                )
            )
            .distinct()
        )
        
        count_query = (
            select(func.count(func.distinct(Vehicle.id)))
            .join(Inspection, Inspection.vehicle_id == Vehicle.id)
            .join(InspectionResult, InspectionResult.inspection_id == Inspection.id)
            .join(InspectionField, InspectionField.id == InspectionResult.inspection_field_id)
            .where(
                and_(
                    InspectionField.field_name.ilike(f"%{field_name}%"),
                    InspectionResult.filed_value.ilike(f"%{problem_value}%")
                )
            )
        )
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_vehicle_history(self, vehicle_id: UUID) -> List[Inspection]:
        """
        Get the full inspection history of a specific car, ordered by newest first.
        Includes nested results and images.
        """
        query = (
            select(Inspection)
            .where(Inspection.vehicle_id == vehicle_id)
            .order_by(Inspection.inspection_date.desc())
            .options(
                selectinload(Inspection.inspector),
                selectinload(Inspection.customer),
                selectinload(Inspection.results).selectinload(InspectionResult.field),
                selectinload(Inspection.images)
            )
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())
